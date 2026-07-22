import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'

import VariantTags from './VariantTags'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

test('renders a summary row for each tag type with saved variants', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <VariantTags projectGuid="R0237_1000_genomes_demo" />
      </MemoryRouter>
    </Provider>,
  )

  // Excluded has numTags 0, so it should not get a summary row
  const rows = wrapper.find('TagSummary')
  expect(rows.length).toEqual(2)

  const reviewRow = rows.at(0)
  expect(reviewRow.find('b').text()).toEqual('2')
  expect(reviewRow.find('a').text()).toEqual('Review')
  expect(reviewRow.find('a').prop('href')).toEqual('/project/R0237_1000_genomes_demo/saved_variants/Review')

  const tier1Row = rows.at(1)
  expect(tier1Row.find('b').text()).toEqual('1')
  expect(tier1Row.find('a').text()).toEqual('Tier 1 - Phenotype not delineated')
  expect(tier1Row.find('HelpIcon').exists()).toBe(true)
})

test('does not show a help icon for tag types without a description', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <VariantTags projectGuid="R0237_1000_genomes_demo" />
      </MemoryRouter>
    </Provider>,
  )

  const reviewRow = wrapper.find('TagSummary').at(0)
  expect(reviewRow.find('HelpIcon').exists()).toBe(false)
})

test('uses analysis group tag type counts when an analysisGroupGuid is provided', () => {
  const store = configureStore()({
    ...STATE_WITH_2_FAMILIES,
    familyTagTypeCounts: {
      F011652_1: { Review: 2, 'Tier 1 - Phenotype not delineated': 1 },
      F011652_2: { Excluded: 5 },
    },
  })
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <VariantTags projectGuid="R0237_1000_genomes_demo" analysisGroupGuid="AG0000183_test_group" />
      </MemoryRouter>
    </Provider>,
  )

  // AG0000183_test_group only contains family F011652_1, whose tagged variants are 2 Review and 1 Tier 1
  const rows = wrapper.find('TagSummary')
  expect(rows.length).toEqual(2)

  const reviewRow = rows.at(0)
  expect(reviewRow.find('b').text()).toEqual('2')
  expect(reviewRow.find('a').prop('href')).toEqual(
    '/project/R0237_1000_genomes_demo/saved_variants/analysis_group/AG0000183_test_group/Review',
  )

  const tier1Row = rows.at(1)
  expect(tier1Row.find('b').text()).toEqual('1')
  expect(tier1Row.find('a').prop('href')).toEqual(
    '/project/R0237_1000_genomes_demo/saved_variants/analysis_group/AG0000183_test_group/Tier 1 - Phenotype not delineated',
  )
})

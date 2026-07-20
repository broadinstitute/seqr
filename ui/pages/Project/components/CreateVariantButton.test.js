import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'

import CreateVariantButtons from './CreateVariantButton'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

const FAMILY = STATE_WITH_2_FAMILIES.familiesByGuid.F011652_1

test('renders manual variant and SV buttons when the project is editable', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <CreateVariantButtons family={FAMILY} />
    </Provider>
  )

  expect(wrapper.text()).toContain('Add Manual Variant')
  expect(wrapper.text()).toContain('Add Manual SV')
})

test('renders nothing when the project is not editable and the user is not an analyst', () => {
  const readOnlyState = {
    ...STATE_WITH_2_FAMILIES,
    projectsByGuid: {
      ...STATE_WITH_2_FAMILIES.projectsByGuid,
      R0237_1000_genomes_demo: { ...STATE_WITH_2_FAMILIES.projectsByGuid.R0237_1000_genomes_demo, canEdit: false },
    },
  }
  const store = configureStore()(readOnlyState)
  const wrapper = mount(
    <Provider store={store}>
      <CreateVariantButtons family={FAMILY} />
    </Provider>
  )

  expect(wrapper.text()).toEqual('')
})

test('renders buttons for a non-editable project when the user is an analyst on an analyst project', () => {
  const analystState = {
    ...STATE_WITH_2_FAMILIES,
    user: { ...STATE_WITH_2_FAMILIES.user, isAnalyst: true },
    projectsByGuid: {
      ...STATE_WITH_2_FAMILIES.projectsByGuid,
      R0237_1000_genomes_demo: {
        ...STATE_WITH_2_FAMILIES.projectsByGuid.R0237_1000_genomes_demo, canEdit: false, isAnalystProject: true,
      },
    },
  }
  const store = configureStore()(analystState)
  const wrapper = mount(
    <Provider store={store}>
      <CreateVariantButtons family={FAMILY} />
    </Provider>
  )

  expect(wrapper.text()).toContain('Add Manual Variant')
  expect(wrapper.text()).toContain('Add Manual SV')
})

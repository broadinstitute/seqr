import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import { MemoryRouter } from 'react-router-dom'

import VariantTagTypeBar, { getSavedVariantsLinkPath } from './VariantTagTypeBar'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

const TAG_TYPES = STATE_WITH_2_FAMILIES.projectsByGuid.R0237_1000_genomes_demo.variantTagTypes
const TAG_TYPE_COUNTS = { Review: 2, Excluded: 0, 'Tier 1 - Phenotype not delineated': 1 }

test('renders a bar section per tag type with data, linked to the saved variants page', () => {
  const wrapper = mount(
    <MemoryRouter>
      <VariantTagTypeBar
        projectGuid="R0237_1000_genomes_demo"
        tagTypes={TAG_TYPES}
        tagTypeCounts={TAG_TYPE_COUNTS}
      />
    </MemoryRouter>
  )

  // Only tag types with a non-zero count get a bar section (Excluded has count 0)
  const barSections = wrapper.find('HorizontalStackedBar__BarSection')
  expect(barSections.length).toEqual(2)
  expect(barSections.at(0).prop('color')).toEqual('#668FE3')
  expect(barSections.at(0).find('a').prop('href')).toEqual('/project/R0237_1000_genomes_demo/saved_variants/Review')
  expect(barSections.at(1).find('a').prop('href')).toEqual('/project/R0237_1000_genomes_demo/saved_variants/Tier 1 - Phenotype not delineated')
})

test('shows a no-data message when there are no saved variants', () => {
  const wrapper = mount(
    <MemoryRouter>
      <VariantTagTypeBar
        projectGuid="R0237_1000_genomes_demo"
        tagTypes={TAG_TYPES}
        tagTypeCounts={{}}
      />
    </MemoryRouter>
  )

  expect(wrapper.text()).toContain('No Saved Variants')
  expect(wrapper.find('HorizontalStackedBar__BarSection').exists()).toBe(false)
})

describe('getSavedVariantsLinkPath', () => {
  test('builds a project-level path', () => {
    expect(getSavedVariantsLinkPath({ projectGuid: 'R01' })).toEqual('/project/R01/saved_variants')
  })

  test('builds a family-level path with a tag', () => {
    expect(getSavedVariantsLinkPath({ projectGuid: 'R01', familyGuid: 'F01', tag: 'Excluded' })).toEqual(
      '/project/R01/saved_variants/family/F01/Excluded',
    )
  })

  test('builds an analysis-group path when there is no family', () => {
    expect(getSavedVariantsLinkPath({ projectGuid: 'R01', analysisGroupGuid: 'AG01' })).toEqual(
      '/project/R01/saved_variants/analysis_group/AG01',
    )
  })

  test('prefers family over analysis group when both are given', () => {
    expect(getSavedVariantsLinkPath({ projectGuid: 'R01', familyGuid: 'F01', analysisGroupGuid: 'AG01' })).toEqual(
      '/project/R01/saved_variants/family/F01',
    )
  })
})

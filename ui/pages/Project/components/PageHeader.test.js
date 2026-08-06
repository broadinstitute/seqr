import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'

import cloneDeep from 'lodash/cloneDeep'
import PageHeader from './PageHeader'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

const renderPageHeader = (props, state = STATE_WITH_2_FAMILIES) => mount(
  <Provider store={configureStore()(state)}>
    <MemoryRouter>
      <PageHeader {...props} />
    </MemoryRouter>
  </Provider>,
)

test('renders the project title and an edit button on the project page', () => {
  const wrapper = renderPageHeader({ match: { params: { breadcrumb: 'project_page' } } })

  expect(wrapper.find('Breadcrumb').text()).toContain('1000 Genomes Demo')
  expect(wrapper.find('ButtonLink[content="Edit Project"]').exists()).toBe(true)
})

test('renders the analysis group name in the breadcrumb', () => {
  const wrapper = renderPageHeader({
    match: { url: '/project/R0237_1000_genomes_demo/analysis_group/AG0000183_test_group', params: { breadcrumb: 'analysis_group', breadcrumbId: 'AG0000183_test_group' } },
  })

  expect(wrapper.find('Breadcrumb').text()).toContain('Analysis Group: Test Group')
})

test('renders the family description on the family page', () => {
  const wrapper = renderPageHeader({
    match: {
      url: '/project/R0237_1000_genomes_demo/family_page/F011652_1',
      params: { breadcrumb: 'family_page', breadcrumbId: 'F011652_1' },
    },
  })

  expect(wrapper.find('Breadcrumb').text()).toContain('Family: 1')
})

test('renders nothing when there is no current project', () => {
  const store = configureStore()({ ...STATE_WITH_2_FAMILIES, currentProjectGuid: null })
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <PageHeader match={{ params: { breadcrumb: 'project_page' } }} />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.find('Breadcrumb').exists()).toBe(false)
})

test('renders the consent code when the user is a PM viewing a project with a consent code', () => {
  const store = configureStore()({
    ...STATE_WITH_2_FAMILIES,
    user: { ...STATE_WITH_2_FAMILIES.user, isPm: true },
  })
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <PageHeader match={{ params: { breadcrumb: 'project_page' } }} />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.text()).toContain('Consent Code:')
})

test('renders the project title for an unrecognized breadcrumb', () => {
  const wrapper = renderPageHeader({ match: { params: { breadcrumb: 'other_page' } } })

  expect(wrapper.find('Breadcrumb').text()).toContain('1000 Genomes Demo')
  expect(wrapper.find('ButtonLink[content="Edit Project"]').exists()).toBe(false)
})

test('renders no description on the family page for the matchmaker exchange and rna-seq results sections', () => {
  const wrapper = renderPageHeader({
    match: {
      url: '/project/R0237_1000_genomes_demo/family_page/F011652_1/matchmaker_exchange',
      params: { breadcrumb: 'family_page', breadcrumbId: 'F011652_1', breadcrumbIdSection: 'matchmaker_exchange' },
    },
  })

  expect(wrapper.find('Breadcrumb').text()).toContain('Family: 1')
  expect(wrapper.find('InlineHeader').exists()).toBe(false)
})

test('falls back to an empty family display name on the family page', () => {
  const state = cloneDeep(STATE_WITH_2_FAMILIES)
  delete state.familiesByGuid.F011652_1.displayName
  const wrapper = renderPageHeader({
    match: {
      url: '/project/R0237_1000_genomes_demo/family_page/F011652_1',
      params: { breadcrumb: 'family_page', breadcrumbId: 'F011652_1' },
    },
  }, state)

  expect(wrapper.find('Breadcrumb').text()).toContain('Family:')
})

test('renders an rnaseq_results breadcrumb subsection with the individual id', () => {
  const wrapper = renderPageHeader({
    match: {
      url: '/project/R0237_1000_genomes_demo/family_page/F011652_1/rnaseq_results/I021476_na19678_1',
      params: {
        breadcrumb: 'family_page',
        breadcrumbId: 'F011652_1',
        breadcrumbIdSection: 'rnaseq_results',
        breadcrumbIdSubsection: 'I021476_na19678_1',
      },
    },
  })

  expect(wrapper.find('Breadcrumb').text()).toContain('RNAseq: NA19678')

  const noIdWrapper = renderPageHeader({
    match: {
      url: '/project/R0237_1000_genomes_demo/family_page/F011652_1/rnaseq_results/I12345',
      params: {
        breadcrumb: 'family_page',
        breadcrumbId: 'F011652_1',
        breadcrumbIdSection: 'rnaseq_results',
        breadcrumbIdSubsection: 'I12345',
      },
    },
  })

  expect(noIdWrapper.find('Breadcrumb').text()).toEqual('Project1000 Genomes DemoFamily: 1RNAseq: ')
})

test('renders a generic breadcrumb id section on the family page', () => {
  const wrapper = renderPageHeader({
    match: {
      url: '/project/R0237_1000_genomes_demo/family_page/F011652_1/notes',
      params: { breadcrumb: 'family_page', breadcrumbId: 'F011652_1', breadcrumbIdSection: 'notes' },
    },
  })

  expect(wrapper.find('Breadcrumb').text()).toContain('Notes')
})

test('falls back to an empty analysis group name in the breadcrumb', () => {
  const wrapper = renderPageHeader({
    match: { url: '/project/R0237_1000_genomes_demo/analysis_group/AG0000181_test_group_2', params: { breadcrumb: 'analysis_group', breadcrumbId: 'AG0000181_test_group_2' } },
  })

  expect(wrapper.find('Breadcrumb').text()).toContain('Analysis Group:')
})

test('renders saved_variants breadcrumb sections for the variant, family, analysis_group, and generic variant pages', () => {
  const variantWrapper = renderPageHeader({
    match: {
      url: '/project/R0237_1000_genomes_demo/saved_variants/variant/SV1',
      params: { breadcrumb: 'saved_variants', variantPage: 'variant' },
    },
  })
  expect(variantWrapper.find('Breadcrumb').text()).toContain('Saved VariantsVariant')

  const familyNoTagWrapper = renderPageHeader({
    match: {
      url: '/project/R0237_1000_genomes_demo/saved_variants/family/F011652_2',
      params: { breadcrumb: 'saved_variants', variantPage: 'family', breadcrumbId: 'F011652_2' },
    },
  })
  expect(familyNoTagWrapper.find('Breadcrumb').text()).toContain('Family: 2')

  const familyWithTagWrapper = renderPageHeader({
    match: {
      url: '/project/R0237_1000_genomes_demo/saved_variants/family/F011652_2/Review',
      params: { breadcrumb: 'saved_variants', variantPage: 'family', breadcrumbId: 'F011652_2', tag: 'Review' },
    },
  })
  expect(familyWithTagWrapper.find('Breadcrumb').text()).toContain('Review')

  const state = cloneDeep(STATE_WITH_2_FAMILIES)
  delete state.familiesByGuid.F011652_1.displayName
  const familyNoNameWrapper = renderPageHeader({
    match: {
      url: '/project/R0237_1000_genomes_demo/saved_variants/family/F011652_1',
      params: { breadcrumb: 'saved_variants', variantPage: 'family', breadcrumbId: 'F011652_1' },
    },
  }, state)
  expect(familyNoNameWrapper.find('Breadcrumb').text()).toContain('Family:')

  const analysisGroupNoTagWrapper = renderPageHeader({
    match: {
      url: '/project/R0237_1000_genomes_demo/saved_variants/analysis_group/AG0000183_test_group',
      params: { breadcrumb: 'saved_variants', variantPage: 'analysis_group', breadcrumbId: 'AG0000183_test_group' },
    },
  })
  expect(analysisGroupNoTagWrapper.find('Breadcrumb').text()).toContain('Analysis Group: Test Group')

  const analysisGroupWithTagWrapper = renderPageHeader({
    match: {
      url: '/project/R0237_1000_genomes_demo/saved_variants/analysis_group/AG0000183_test_group/Review',
      params: {
        breadcrumb: 'saved_variants', variantPage: 'analysis_group', breadcrumbId: 'AG0000183_test_group', tag: 'Review',
      },
    },
  })
  expect(analysisGroupWithTagWrapper.find('Breadcrumb').text()).toContain('Review')

  const analysisGroupNoNameState = cloneDeep(STATE_WITH_2_FAMILIES)
  delete analysisGroupNoNameState.analysisGroupsByGuid.AG0000183_test_group.name
  const analysisGroupNoNameWrapper = renderPageHeader({
    match: {
      url: '/project/R0237_1000_genomes_demo/saved_variants/analysis_group/AG0000183_test_group',
      params: { breadcrumb: 'saved_variants', variantPage: 'analysis_group', breadcrumbId: 'AG0000183_test_group' },
    },
  }, analysisGroupNoNameState)
  expect(analysisGroupNoNameWrapper.find('Breadcrumb').text()).toContain('Analysis Group:')

  const genericVariantPageWrapper = renderPageHeader({
    match: {
      url: '/project/R0237_1000_genomes_demo/saved_variants/some_other_page',
      params: { breadcrumb: 'saved_variants', variantPage: 'some_other_page' },
    },
  })
  expect(genericVariantPageWrapper.find('Breadcrumb').text()).toContain('some_other_page')
})

test('shows an AnVIL loading message when search is disabled for a project with a workspace', () => {
  const disabledState = {
    ...STATE_WITH_2_FAMILIES,
    datasetsByGuid: {},
  }
  const wrapper = renderPageHeader({ match: { params: { breadcrumb: 'project_page' } } }, disabledState)

  const popup = wrapper.find('Popup').filterWhere(n => typeof n.prop('content') === 'string')
  expect(popup.exists()).toBe(true)
  expect(popup.first().prop('content')).toContain('Loading data from AnVIL to seqr is a slow process')
})

test('renders a case review link when the project has case review enabled', () => {
  const caseReviewState = cloneDeep(STATE_WITH_2_FAMILIES)
  caseReviewState.projectsByGuid.R0237_1000_genomes_demo.hasCaseReview = true
  const wrapper = renderPageHeader({ match: { params: { breadcrumb: 'project_page' } } }, caseReviewState)

  expect(wrapper.text()).toContain('Case Review')
})

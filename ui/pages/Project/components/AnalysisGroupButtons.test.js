import React from 'react'
import { mount, configure } from 'enzyme'
import configureStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import { Provider } from 'react-redux'
import { MemoryRouter, Router } from 'react-router-dom'
import { createMemoryHistory } from 'history'
import { CATEGORY_FAMILY_FILTERS } from 'shared/utils/constants'
import { UpdateAnalysisGroupButton, DeleteAnalysisGroupButton } from './AnalysisGroupButtons'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

// Renders a canvas-based pedigree diagram via a third-party library that does not work in jsdom.
// Not the subject of this test file - stub it out so mounting the family table does not crash.
jest.mock('shared/components/panel/view-pedigree-image/PedigreeImagePanel', () => function MockPedigreeImagePanel() {
  return <div className="mock-pedigree-image" />
})

const ANALYSIS_GROUP = {
  ...STATE_WITH_2_FAMILIES.analysisGroupsByGuid.AG0000183_test_group, workspaceNamespace: undefined,
}

const WORKSPACE_ANALYSIS_GROUP = STATE_WITH_2_FAMILIES.analysisGroupsByGuid.AG0000183_test_group

configure({ adapter: new Adapter() })

const renderWithStore = (Component, props, state = STATE_WITH_2_FAMILIES) => mount(
  <Provider store={configureStore()(state)}>
    <MemoryRouter>
      <Component {...props} />
    </MemoryRouter>
  </Provider>,
)

test('renders a create button when no analysis group is specified', () => {
  const wrapper = renderWithStore(UpdateAnalysisGroupButton, {})

  expect(wrapper.find('ButtonLink').prop('content')).toEqual('Create New Analysis Group')
})

test('renders an edit button for an existing analysis group', () => {
  const wrapper = renderWithStore(UpdateAnalysisGroupButton, { analysisGroup: ANALYSIS_GROUP })

  expect(wrapper.find('ButtonLink').prop('content')).toEqual('Edit Analysis Group')
})

test('renders a delete button for an existing analysis group', () => {
  const wrapper = renderWithStore(DeleteAnalysisGroupButton, { analysisGroup: ANALYSIS_GROUP })

  expect(wrapper.find('ButtonLink').prop('content')).toEqual('Delete Analysis Group')
})

test('does not render an edit button for an analysis group with a workspaceNamespace when the user is not a PM', () => {
  const wrapper = renderWithStore(UpdateAnalysisGroupButton, { analysisGroup: WORKSPACE_ANALYSIS_GROUP })

  expect(wrapper.find('ButtonLink').exists()).toBe(false)
})

test('renders an edit button for an analysis group with a workspaceNamespace when the user is a PM', () => {
  const state = { ...STATE_WITH_2_FAMILIES, user: { ...STATE_WITH_2_FAMILIES.user, isPm: true } }
  const wrapper = renderWithStore(UpdateAnalysisGroupButton, { analysisGroup: WORKSPACE_ANALYSIS_GROUP }, state)

  expect(wrapper.find('ButtonLink').prop('content')).toEqual('Edit Analysis Group')
})

test('does not render a delete button for an analysis group with a workspaceNamespace', () => {
  const wrapper = renderWithStore(DeleteAnalysisGroupButton, { analysisGroup: WORKSPACE_ANALYSIS_GROUP })

  expect(wrapper.find('ButtonLink').exists()).toBe(false)
})

test('does not render a delete button for an analysis group with a workspaceNamespace when the user is a PM', () => {
  const state = { ...STATE_WITH_2_FAMILIES, user: { ...STATE_WITH_2_FAMILIES.user, isPm: true } }
  const wrapper = renderWithStore(DeleteAnalysisGroupButton, { analysisGroup: WORKSPACE_ANALYSIS_GROUP }, state)

  expect(wrapper.find('ButtonLink').exists()).toBe(false)
})

test('navigates to the project page when a delete succeeds', () => {
  const history = createMemoryHistory()
  const wrapper = mount(
    <Provider store={configureStore()(STATE_WITH_2_FAMILIES)}>
      <Router history={history}>
        <DeleteAnalysisGroupButton analysisGroup={ANALYSIS_GROUP} />
      </Router>
    </Provider>,
  )

  wrapper.find('DispatchRequestButton').first().prop('onSuccess')()

  expect(history.location.pathname).toEqual('/project/R0237_1000_genomes_demo/project_page')
})

test('renders the family upload and family table fields for a static analysis group when the create modal is open', () => {
  const store = configureStore([thunk])({
    ...STATE_WITH_2_FAMILIES,
    modal: { 'createAnalysisGroup-R0237_1000_genomes_demo': { open: true } },
  })
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <UpdateAnalysisGroupButton />
      </MemoryRouter>
    </Provider>,
  )

  const familyGuidsField = wrapper.find('ForwardRef(Field)[name="familyGuids"]')
  expect(familyGuidsField.prop('validate')(undefined)).toEqual('Families are required')
  expect(familyGuidsField.prop('validate')(['F1'])).toBeUndefined()
  expect(familyGuidsField.prop('format')(undefined)).toEqual({})
  expect(familyGuidsField.prop('format')(['a', 'b'])).toEqual({ a: true, b: true })
  expect(familyGuidsField.prop('parse')({ a: true, b: false, c: true })).toEqual(['a', 'c'])

  const parseUpload = wrapper.find('ForwardRef(Field)[name="uploadedFamilyIds"]').last().prop('parse')
  expect(parseUpload({ errors: ['bad row'] })).toEqual({ errors: [], info: ['bad row'] })
  expect(parseUpload({ other: 'unchanged' })).toEqual({ other: 'unchanged' })

  const { familyId, familyGuid } = STATE_WITH_2_FAMILIES.familiesByGuid.F011652_1
  expect(parseUpload({ parsedData: [[familyId]] })).toEqual({
    parsedData: [[familyId]],
    familyGuids: [familyGuid],
    info: ['Uploaded 1 families'],
  })
  expect(parseUpload({ parsedData: [[familyId], ['missing-id']] })).toEqual({
    parsedData: [[familyId], ['missing-id']],
    familyGuids: [familyGuid],
    info: ['Uploaded 1 families', 'Unable to find families with the following IDs: missing-id'],
  })
})

test('renders the criteria fields with a required first criteria for a dynamic analysis group', () => {
  const store = configureStore([thunk])({
    ...STATE_WITH_2_FAMILIES,
    modal: { 'createDynamicAnalysisGroup-R0237_1000_genomes_demo': { open: true } },
  })
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <UpdateAnalysisGroupButton createDynamic />
      </MemoryRouter>
    </Provider>,
  )

  const firstCategory = Object.keys(CATEGORY_FAMILY_FILTERS)[0]
  const criteriaField = wrapper.find(`ForwardRef(Field)[name="criteria.${firstCategory}"]`)
  expect(criteriaField.prop('validate')(null, { criteria: { [firstCategory]: ['x'] } })).toBeUndefined()
  expect(criteriaField.prop('validate')(null, {})).toEqual('At least one criteria is required')

  expect(wrapper.find('ForwardRef(Field)[name="familyGuids"]').exists()).toBe(false)
})

test('renders the AnVIL workspace fields for a static analysis group when the user is a PM on an analyst project', () => {
  const state = {
    ...STATE_WITH_2_FAMILIES,
    user: { ...STATE_WITH_2_FAMILIES.user, isPm: true },
    projectsByGuid: {
      ...STATE_WITH_2_FAMILIES.projectsByGuid,
      R0237_1000_genomes_demo: {
        ...STATE_WITH_2_FAMILIES.projectsByGuid.R0237_1000_genomes_demo, isAnalystProject: true,
      },
    },
    modal: { 'createAnalysisGroup-R0237_1000_genomes_demo': { open: true } },
  }
  const store = configureStore([thunk])(state)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <UpdateAnalysisGroupButton />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.find('ForwardRef(Field)[name="workspaceNamespace"]').exists()).toBe(true)
  expect(wrapper.find('ForwardRef(Field)[name="workspaceName"]').exists()).toBe(true)
})

import React from 'react'
import { mount, configure } from 'enzyme'
import configureStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import { Provider } from 'react-redux'
import { MemoryRouter, Router } from 'react-router-dom'
import { createMemoryHistory } from 'history'
import { CATEGORY_FAMILY_FILTERS } from 'shared/utils/constants'
import { flushAll, getLastFetchUrl, getLastFetchBody } from 'shared/utils/testHelpers'
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

  expect(wrapper.find('ForwardRef(Field)[name="workspaceNamespace"]').exists()).toBe(false)
  expect(wrapper.find('ForwardRef(Field)[name="workspaceName"]').exists()).toBe(false)

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

test('renders an icon-only create button with no button text', () => {
  const wrapper = renderWithStore(UpdateAnalysisGroupButton, { iconOnly: true })

  expect(wrapper.find('ButtonLink').prop('content')).toBeFalsy()
})

test('renders an icon-only delete button with no button text', () => {
  const wrapper = renderWithStore(
    DeleteAnalysisGroupButton, { analysisGroup: ANALYSIS_GROUP, iconOnly: true },
  )

  expect(wrapper.find('ButtonLink').prop('content')).toBeFalsy()
})

test('validates that a name value is present', () => {
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

  const nameField = wrapper.find('ForwardRef(Field)[name="name"]')
  expect(nameField.prop('validate')('Some Name')).toBeUndefined()
  expect(nameField.prop('validate')('')).toEqual('Name is required')
})

test('merges uploaded family guids into the family guids field via the form calculate decorator', () => {
  const editModalId = `editAnalysisGroup-${ANALYSIS_GROUP.analysisGroupGuid}`
  const store = configureStore([thunk])({
    ...STATE_WITH_2_FAMILIES,
    modal: { [editModalId]: { open: true } },
  })
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <UpdateAnalysisGroupButton analysisGroup={ANALYSIS_GROUP} />
      </MemoryRouter>
    </Provider>,
  )

  const uploadedFamilyIdsField = wrapper.find('ForwardRef(Field)[name="uploadedFamilyIds"]').last()
  uploadedFamilyIdsField.prop('onChange')({ familyGuids: ['F011652_2'] })
  wrapper.update()

  let familyGuidsField = wrapper.find('Memo()').filterWhere(n => n.prop('idField') === 'familyGuid')
  expect(familyGuidsField.first().prop('value')).toEqual({ F011652_1: true, F011652_2: true })

  // an upload with no parsed family guids does not add anything new
  wrapper.find('ForwardRef(Field)[name="uploadedFamilyIds"]').last().prop('onChange')({})
  wrapper.update()

  familyGuidsField = wrapper.find('Memo()').filterWhere(n => n.prop('idField') === 'familyGuid')
  expect(familyGuidsField.first().prop('value')).toEqual({ F011652_1: true, F011652_2: true })
})

test('merges uploaded family guids into an empty family guids field via the form calculate decorator', () => {
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

  const uploadedFamilyIdsField = wrapper.find('ForwardRef(Field)[name="uploadedFamilyIds"]').last()
  uploadedFamilyIdsField.prop('onChange')({ familyGuids: ['F011652_1'] })
  wrapper.update()

  const familyGuidsField = wrapper.find('Memo()').filterWhere(n => n.prop('idField') === 'familyGuid')
  expect(familyGuidsField.first().prop('value')).toEqual({ F011652_1: true })
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

test('submits a new static analysis group', async () => {
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

  wrapper.find('FormWrapper').prop('onSubmit')({ name: 'New Group', familyGuids: ['F011652_1'] })
  await flushAll()

  expect(getLastFetchUrl()).toEqual('/api/project/R0237_1000_genomes_demo/analysis_groups/create')
  expect(getLastFetchBody()).toEqual({ name: 'New Group', familyGuids: ['F011652_1'] })
})

test('submits a new dynamic analysis group', async () => {
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

  const criteria = { analysisStatus: ['Q'] }
  wrapper.find('FormWrapper').prop('onSubmit')({ name: 'Dynamic Group', criteria })
  await flushAll()

  expect(getLastFetchUrl()).toEqual('/api/project/R0237_1000_genomes_demo/dynamic_analysis_groups/create')
  expect(getLastFetchBody()).toEqual({ name: 'Dynamic Group', criteria })
})

test('submits an update to an existing analysis group', async () => {
  const editModalId = `editAnalysisGroup-${ANALYSIS_GROUP.analysisGroupGuid}`
  const store = configureStore([thunk])({
    ...STATE_WITH_2_FAMILIES,
    modal: { [editModalId]: { open: true } },
  })
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <UpdateAnalysisGroupButton analysisGroup={ANALYSIS_GROUP} />
      </MemoryRouter>
    </Provider>,
  )

  wrapper.find('FormWrapper').prop('onSubmit')({ ...ANALYSIS_GROUP, name: 'Updated Name' })
  await flushAll()

  expect(getLastFetchUrl()).toEqual(
    `/api/project/R0237_1000_genomes_demo/analysis_groups/${ANALYSIS_GROUP.analysisGroupGuid}/update`,
  )
  expect(getLastFetchBody()).toEqual({ ...ANALYSIS_GROUP, name: 'Updated Name' })
})

test('dispatches a delete request for an existing analysis group', async () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <DeleteAnalysisGroupButton analysisGroup={ANALYSIS_GROUP} />
      </MemoryRouter>
    </Provider>,
  )

  wrapper.find('DispatchRequestButton').first().prop('onSubmit')()
  await flushAll()

  expect(getLastFetchUrl()).toEqual(
    `/api/project/R0237_1000_genomes_demo/analysis_groups/${ANALYSIS_GROUP.analysisGroupGuid}/delete`,
  )
  expect(getLastFetchBody()).toEqual({ ...ANALYSIS_GROUP, delete: true })
})

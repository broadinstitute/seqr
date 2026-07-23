import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'

import {
  mockFetchResponse, mockFetchRejection, flushAll, getLastFetchUrl, getLastFetchBody,
} from 'shared/utils/testHelpers'
import ProjectCollaborators from './ProjectCollaborators'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

test('renders each collaborator email with an edit and add button', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  const wrapper = mount(
    <Provider store={store}>
      <ProjectCollaborators />
    </Provider>,
  )

  expect(wrapper.find('a[href="mailto:test1@broadinstitute.org"]').exists()).toBe(true)
  expect(wrapper.find('a[href="mailto:test2@broadinstitute.org"]').exists()).toBe(true)
  expect(wrapper.find('ButtonLink[content="Add Collaborator"]').exists()).toBe(true)
})

test('renders the add collaborator form and submits a new collaborator', () => {
  const state = {
    ...STATE_WITH_2_FAMILIES,
    modal: { addCollaborator: { open: true } },
    userOptionsLoading: { isLoading: false },
  }
  const store = configureStore(state)

  const wrapper = mount(
    <Provider store={store}>
      <ProjectCollaborators />
    </Provider>,
  )

  const userField = wrapper.find('ForwardRef(Field)[name="user"]')
  expect(userField.exists()).toBe(true)

  const email = 'newuser@broadinstitute.org'
  expect(userField.prop('parse')(email)).toEqual({ email })
  expect(userField.prop('parse')({ username: 'existing', email })).toEqual({ username: 'existing', email })
  expect(userField.prop('format')({ username: 'existing', email })).toEqual({ username: 'existing', email })
  expect(userField.prop('format')({ email })).toEqual(email)
  expect(userField.prop('format')(null)).toBeFalsy()
  expect(userField.prop('validate')({ email })).toBeUndefined()
  expect(userField.prop('validate')(null)).toBeTruthy()

  const addButton = wrapper.find('[modalId="addCollaborator"]')
  expect(addButton.exists()).toBe(true)
  expect(() => addButton.prop('onSubmit')({ user: { email } })).not.toThrow()
})

test('renders analysis group workspace collaborators when the collaborator has a display name', () => {
  const state = {
    ...STATE_WITH_2_FAMILIES,
    analysisGroupsByGuid: {
      ...STATE_WITH_2_FAMILIES.analysisGroupsByGuid,
      AG0000183_test_group: {
        ...STATE_WITH_2_FAMILIES.analysisGroupsByGuid.AG0000183_test_group,
        collaborators: [{ email: 'group-collab@broadinstitute.org', displayName: 'Group Collaborator' }],
      },
    },
  }
  const store = configureStore(state)

  const wrapper = mount(
    <Provider store={store}>
      <ProjectCollaborators analysisGroupGuid="AG0000183_test_group" />
    </Provider>,
  )

  expect(wrapper.find('a[href="mailto:group-collab@broadinstitute.org"]').exists()).toBe(true)
  expect(wrapper.text()).toContain('Group Collaborator -')
  expect(wrapper.find('a[href="mailto:test1@broadinstitute.org"]').exists()).toBe(false)
})

test('renders collaborator groups and the AnVIL managed message', () => {
  const project = STATE_WITH_2_FAMILIES.projectsByGuid.R0237_1000_genomes_demo
  const state = {
    ...STATE_WITH_2_FAMILIES,
    projectsByGuid: {
      ...STATE_WITH_2_FAMILIES.projectsByGuid,
      R0237_1000_genomes_demo: {
        ...project,
        canEdit: true,
        workspaceName: 'anvil-workspace',
        collaboratorGroups: [{ name: 'group1', hasEditPermissions: false }],
      },
    },
    user: { ...STATE_WITH_2_FAMILIES.user, isAnvil: true },
  }
  const store = configureStore(state)

  const wrapper = mount(
    <Provider store={store}>
      <ProjectCollaborators />
    </Provider>,
  )

  expect(wrapper.text()).toContain('group1')
  expect(wrapper.text()).toContain('Collaborators fetched from AnVIL')
  const addButton = wrapper.find('[modalId="addCollaborator"]')
  expect(addButton.exists()).toBe(false)
})

test('fetches collaborators from the server and dispatches on success for an analysis group without cached collaborators', async () => {
  mockFetchResponse({ projectsByGuid: {} })
  const store = configureStore(STATE_WITH_2_FAMILIES)

  mount(
    <Provider store={store}>
      <ProjectCollaborators analysisGroupGuid="AG0000183_test_group" />
    </Provider>,
  )

  expect(getLastFetchUrl()).toEqual(
    '/api/project/R0237_1000_genomes_demo/analysis_groups/AG0000183_test_group/get_collaborators?',
  )

  await flushAll()

  expect(store.getActions().some(action => action.type === 'RECEIVE_DATA')).toBe(true)
  expect(store.getActions().some(action => action.type === 'RECEIVE_PROJECT_COLLABORATORS')).toBe(true)
})

test('dispatches an error action when fetching collaborators for an analysis group fails', async () => {
  mockFetchRejection(new Error('fail'))
  const store = configureStore(STATE_WITH_2_FAMILIES)

  mount(
    <Provider store={store}>
      <ProjectCollaborators analysisGroupGuid="AG0000183_test_group" />
    </Provider>,
  )

  await flushAll()

  expect(store.getActions().some(
    action => action.type === 'RECEIVE_PROJECT_COLLABORATORS' && action.error === 'fail',
  )).toBe(true)
})

test('renders the add collaborator group form and submits a new group', () => {
  const project = STATE_WITH_2_FAMILIES.projectsByGuid.R0237_1000_genomes_demo
  const state = {
    ...STATE_WITH_2_FAMILIES,
    projectsByGuid: {
      ...STATE_WITH_2_FAMILIES.projectsByGuid,
      R0237_1000_genomes_demo: { ...project, canEdit: true },
    },
    modal: { 'addCollaborator Group': { open: true } },
  }
  const store = configureStore(state)

  const wrapper = mount(
    <Provider store={store}>
      <ProjectCollaborators />
    </Provider>,
  )

  const addGroupButton = wrapper.find('[modalId="addCollaborator Group"]')
  expect(addGroupButton.exists()).toBe(true)

  addGroupButton.prop('onSubmit')({ name: 'newGroup', hasEditPermissions: true })

  expect(getLastFetchUrl()).toEqual('/api/project/R0237_1000_genomes_demo/collaboratorGroups/newGroup/update')
  expect(getLastFetchBody()).toEqual({ name: 'newGroup', hasEditPermissions: true })
})

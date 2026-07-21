import React from 'react'
import { mount, configure } from 'enzyme'
import configureStore from 'redux-mock-store'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'
import { UpdateAnalysisGroupButton, DeleteAnalysisGroupButton } from './AnalysisGroupButtons'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

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

import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import { MemoryRouter, Route } from 'react-router-dom'

import { getLastFetchUrl } from 'shared/utils/testHelpers'
import Project from './Project'

jest.mock('./components/ProjectPageUI', () => () => <div>ProjectPageUI</div>)
jest.mock('./components/CaseReview', () => () => <div>CaseReview</div>)
jest.mock('./components/FamilyPage', () => () => <div>FamilyPageRouter</div>)
jest.mock('./components/Matchmaker', () => () => <div>Matchmaker</div>)
jest.mock('./components/SavedVariants', () => () => <div>SavedVariants</div>)

configure({ adapter: new Adapter() })

const PROJECT_GUID = 'R0237_1000_genomes_demo'

const renderProject = (path, { project, loading } = {}) => {
  const state = {
    currentProjectGuid: PROJECT_GUID,
    projectsByGuid: project ? { [PROJECT_GUID]: { projectGuid: PROJECT_GUID, ...project } } : {},
    projectDetailsLoading: { isLoading: !!loading },
  }
  const store = configureStore([thunk])(state)
  return mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={[path]}>
        <Route path="/project/:projectGuid" component={Project} />
      </MemoryRouter>
    </Provider>,
  )
}

test('loads the current project on mount and unloads it on unmount', () => {
  const state = {
    currentProjectGuid: PROJECT_GUID,
    projectsByGuid: { [PROJECT_GUID]: { projectGuid: PROJECT_GUID } },
    projectDetailsLoading: { isLoading: false },
  }
  const store = configureStore([thunk])(state)
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter initialEntries={[`/project/${PROJECT_GUID}/project_page`]}>
        <Route path="/project/:projectGuid" component={Project} />
      </MemoryRouter>
    </Provider>,
  )

  expect(getLastFetchUrl()).toEqual(`/api/project/${PROJECT_GUID}/details?`)

  wrapper.unmount()

  const actions = store.getActions()
  expect(actions.some(action => action.newValue === null)).toBe(true)
})

test('renders a loader while the project is loading', () => {
  const wrapper = renderProject(`/project/${PROJECT_GUID}/project_page`, { loading: true })

  expect(wrapper.find('Loader').exists()).toBe(true)
})

test('renders Error404 when the project failed to load and is not loading', () => {
  const wrapper = renderProject(`/project/${PROJECT_GUID}/project_page`, { loading: false })

  expect(wrapper.text()).toContain('Error 404')
})

test('renders the project page for users with full access', () => {
  const wrapper = renderProject(`/project/${PROJECT_GUID}/project_page`, { project: { partialAccess: false } })

  expect(wrapper.text()).toContain('ProjectPageUI')
})

test('renders Error404 for the project page route when the user only has partial access', () => {
  const wrapper = renderProject(`/project/${PROJECT_GUID}/project_page`, { project: { partialAccess: true } })

  expect(wrapper.text()).toContain('Error 404')
})

test('renders case review for users with full access to a project with case review enabled', () => {
  const wrapper = renderProject(
    `/project/${PROJECT_GUID}/case_review`,
    { project: { partialAccess: false, hasCaseReview: true } },
  )

  expect(wrapper.text()).toContain('CaseReview')
})

test('renders Error404 for the case review route when case review is not enabled', () => {
  const wrapper = renderProject(
    `/project/${PROJECT_GUID}/case_review`,
    { project: { partialAccess: false, hasCaseReview: false } },
  )

  expect(wrapper.text()).toContain('Error 404')
})

test('renders Error404 for the case review route when the user only has partial access', () => {
  const wrapper = renderProject(
    `/project/${PROJECT_GUID}/case_review`,
    { project: { partialAccess: true, hasCaseReview: true } },
  )

  expect(wrapper.text()).toContain('Error 404')
})

test('renders the analysis group page regardless of partial access', () => {
  const wrapper = renderProject(
    `/project/${PROJECT_GUID}/analysis_group/AG0000183_test_group`,
    { project: { partialAccess: true } },
  )

  expect(wrapper.text()).toContain('ProjectPageUI')
})

test('renders the matchmaker exchange page for a family', () => {
  const wrapper = renderProject(`/project/${PROJECT_GUID}/family_page/F011652_1/matchmaker_exchange`, { project: {} })

  expect(wrapper.text()).toContain('Matchmaker')
})

test('renders the family page', () => {
  const wrapper = renderProject(`/project/${PROJECT_GUID}/family_page/F011652_1`, { project: {} })

  expect(wrapper.text()).toContain('FamilyPageRouter')
})

test('renders the saved variants page', () => {
  const wrapper = renderProject(`/project/${PROJECT_GUID}/saved_variants`, { project: {} })

  expect(wrapper.text()).toContain('SavedVariants')
})

test('renders Error404 for an unrecognized sub-route', () => {
  const wrapper = renderProject(`/project/${PROJECT_GUID}/not_a_real_page`, { project: {} })

  expect(wrapper.text()).toContain('Error 404')
})

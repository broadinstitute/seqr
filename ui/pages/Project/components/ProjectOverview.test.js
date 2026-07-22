import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'
import cloneDeep from 'lodash/cloneDeep'

import ProjectOverview from './ProjectOverview'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

jest.mock('../reducers', () => ({
  ...jest.requireActual('../reducers'),
  loadMmeSubmissions: jest.fn(() => ({ type: 'MOCK_LOAD_MME_SUBMISSIONS' })),
}))

configure({ adapter: new Adapter() })

const PROJECT_GUID = 'R0237_1000_genomes_demo'

const renderProjectOverview = state => mount(
  <Provider store={configureStore()(state)}>
    <MemoryRouter>
      <ProjectOverview familiesLoading={false} overviewLoading={false} />
    </MemoryRouter>
  </Provider>,
)

test('divides content correctly by section for the current project', () => {
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <ProjectOverview familiesLoading={false} overviewLoading={false} />
    </Provider>
  )

  // Each DetailSection renders a <b> title alongside a styled DetailContent with its content.
  // Pair them up by DOM position so we verify each title is associated with its own content,
  // rather than just asserting all expected text appears somewhere on the page.
  const sections = wrapper.find('ProjectOverview__DetailContent').map(content => ({
    title: content.parents().find('b').first().text(),
    content: content.text(),
  }))

  expect(sections).toEqual(expect.arrayContaining([
    {
      title: '2 Families,6 Individuals',
      content: '2 families with 3 individuals',
    },
    {
      title: '1 Families With Data,1 Individuals With Data',
      content: '1 family with 1 individual',
    },
    {
      title: 'Matchmaker Submissions',
      content: 'No Submissions',
    },
    {
      title: 'Genome Version',
      content: 'GRCh38',
    },
    {
      title: 'Exome Datasets',
      content: '3/13/2018 - 1 samples',
    },
    {
      title: 'Analysis Status',
      content: 'No Data',
    },
  ]))
})

test('renders matchmaker submission details when the submissions modal is open', () => {
  const mmeState = cloneDeep(STATE_WITH_2_FAMILIES)
  mmeState.projectsByGuid[PROJECT_GUID].mmeSubmissionCount = 1
  mmeState.projectsByGuid[PROJECT_GUID].mmeDeletedSubmissionCount = 2
  mmeState.modal = { mmeSubmissions: { open: true } }

  const wrapper = renderProjectOverview(mmeState)

  const dataTable = wrapper.find('DataTable').filterWhere(n => n.prop('idField') === 'submissionGuid')
  expect(dataTable.exists()).toBe(true)
  expect(dataTable.text()).toContain('5/9/2018')
  expect(wrapper.text()).toContain('2 removed submissions')
  expect(wrapper.find('[modalId="mmeContact"]').exists()).toBe(true)
})

test('renders family size histogram edge cases and the case review edit button', () => {
  const familyState = cloneDeep(STATE_WITH_2_FAMILIES)
  familyState.projectsByGuid[PROJECT_GUID].hasCaseReview = true
  familyState.familiesByGuid = {
    F1: {
      familyGuid: 'F1',
      projectGuid: PROJECT_GUID,
      individualGuids: ['a1', 'a2', 'a3'],
      parents: [{ maternalGuid: 'm1', paternalGuid: 'p1' }],
    },
    F2: {
      familyGuid: 'F2',
      projectGuid: PROJECT_GUID,
      individualGuids: ['b1', 'b2', 'b3', 'b4'],
      parents: [{ maternalGuid: 'm2', paternalGuid: 'p2' }],
    },
    F4: {
      familyGuid: 'F4',
      projectGuid: PROJECT_GUID,
      individualGuids: ['d1', 'd2', 'd3', 'd4', 'd5', 'd6', 'd7'],
      parents: [
        { maternalGuid: 'm4', paternalGuid: 'p4' },
        { maternalGuid: 'm4', paternalGuid: 'p4' },
      ],
    },
  }

  const wrapper = renderProjectOverview(familyState)

  const text = wrapper.text()
  expect(text).toContain('trio+')
  expect(text).toContain('quad+')
  expect(wrapper.find('[modalName="editFamiliesAndIndividuals"]').exists()).toBe(true)
})

test('shows additional loaded datasets and renders rna datasets', () => {
  const datasetState = cloneDeep(STATE_WITH_2_FAMILIES)
  datasetState.datasetsByGuid = {}
  for (let i = 0; i < 6; i += 1) {
    datasetState.datasetsByGuid[`DS${i}`] = {
      datasetType: 'SNV_INDEL',
      sampleType: 'WES',
      projectGuid: PROJECT_GUID,
      activeIndividuals: ['dummy'],
      inactiveIndividuals: [],
      loadedDate: `2020-01-0${i + 1}T00:00:00.000Z`,
    }
  }
  datasetState.projectsByGuid[PROJECT_GUID].rnaSampleCounts = {
    S: [{ loadedDate: '2021-01-01T00:00:00.000Z', familyCounts: { F011652_1: 3 } }],
  }

  const wrapper = renderProjectOverview(datasetState)

  expect(wrapper.text()).toContain('RNA Splice Outlier Datasets')
  const showMoreButton = wrapper.find('ButtonLink').filterWhere(n => n.text().startsWith('Show '))
  expect(showMoreButton.exists()).toBe(true)

  showMoreButton.first().simulate('click')
  wrapper.update()

  expect(wrapper.find('ButtonLink').filterWhere(n => n.text().startsWith('Show ')).exists()).toBe(false)
})

test('renders anvil workspace details and a message when no datasets are loaded', () => {
  const emptyState = cloneDeep(STATE_WITH_2_FAMILIES)
  emptyState.datasetsByGuid = {}
  emptyState.projectsByGuid[PROJECT_GUID].rnaSampleCounts = {}
  emptyState.user.isPm = true
  emptyState.user.isAnvil = true

  const wrapper = renderProjectOverview(emptyState)

  expect(wrapper.text()).toContain('No Datasets Loaded')
  expect(wrapper.text()).toContain('Where is my data?')
  expect(wrapper.find('[modalId="editAnvilWorkspace"]').exists()).toBe(true)
})

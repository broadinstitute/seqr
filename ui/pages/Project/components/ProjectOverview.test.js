import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'
import cloneDeep from 'lodash/cloneDeep'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import ProjectOverview from './ProjectOverview'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

jest.mock('shared/utils/httpRequestHelper', () => ({
  HttpRequestHelper: jest.fn().mockImplementation(() => ({ get: jest.fn(), post: jest.fn() })),
}))

configure({ adapter: new Adapter() })

const PROJECT_GUID = 'R0237_1000_genomes_demo'

const renderProjectOverview = state => mount(
  <Provider store={configureStore([thunk])(state)}>
    <MemoryRouter>
      <ProjectOverview familiesLoading={false} overviewLoading={false} />
    </MemoryRouter>
  </Provider>,
)

beforeEach(() => {
  HttpRequestHelper.mockClear()
})

test('divides content correctly by section for the current project', () => {
  const wrapper = renderProjectOverview(STATE_WITH_2_FAMILIES)

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
      content: '1 submissions 1 removed submissions',
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
  const wrapper = renderProjectOverview({ ...STATE_WITH_2_FAMILIES, modal: { mmeSubmissions: { open: true } } })

  const dataTable = wrapper.find('DataTable').filterWhere(n => n.prop('idField') === 'submissionGuid')
  expect(dataTable.exists()).toBe(true)
  expect(dataTable.text()).toContain('5/9/2018')
  expect(wrapper.text()).toContain('1 removed submissions')
  expect(wrapper.find('[modalId="mmeContact"]').exists()).toBe(true)
  expect(HttpRequestHelper).toHaveBeenCalledWith(
    `/api/project/${PROJECT_GUID}/get_mme_submissions`, expect.any(Function), expect.any(Function),
  )
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
    F1b: {
      familyGuid: 'F1b',
      projectGuid: PROJECT_GUID,
      individualGuids: ['e1', 'e2', 'e3'],
      parents: [{ maternalGuid: 'm5', paternalGuid: 'p5' }],
    },
    F2: {
      familyGuid: 'F2',
      projectGuid: PROJECT_GUID,
      individualGuids: ['b1', 'b2', 'b3', 'b4'],
      parents: [{ maternalGuid: 'm2', paternalGuid: 'p2' }],
    },
    F3: {
      familyGuid: 'F3',
      projectGuid: PROJECT_GUID,
      individualGuids: ['c1', 'c2', 'c3', 'c4', 'c5', 'c6'],
      parents: [],
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
  expect(text).toContain('trios')
  expect(wrapper.find('[modalName="editFamiliesAndIndividuals"]').exists()).toBe(true)
})

test('shows additional loaded datasets and renders rna datasets', () => {
  const datasetState = {
    ...STATE_WITH_2_FAMILIES,
    datasetsByGuid: {
      ...STATE_WITH_2_FAMILIES.datasetsByGuid,
    },
  }
  for (let i = 0; i < 6; i += 1) {
    datasetState.datasetsByGuid[`DS${i}`] = {
      datasetType: 'SNV_INDEL',
      sampleType: 'WES',
      projectGuid: PROJECT_GUID,
      activeIndividuals: ['dummy', 'dummy2'],
      inactiveIndividuals: [],
      loadedDate: `2020-01-0${i + 1}T12:00:00.000Z`,
    }
  }

  const wrapper = renderProjectOverview(datasetState)

  const datasetsSection = wrapper.find('LoadingSection').filterWhere(
    content => content.find('b').first().text() === 'Exome Datasets',
  ).first()
  expect(datasetsSection.find('b').map(content => content.text())).toEqual([
      'Exome Datasets', 'RNA Expression Outlier Datasets', 'RNA Splice Outlier Datasets'
  ])
  const datasets = [
    ['3/13/2018 - 1 samples', '1/1/2020 - 2 samples', '1/4/2020 - 2 samples', '1/5/2020 - 2 samples', '1/6/2020 - 2 samples'],
    ['1/1/2021 - 3 samples'],
    ['1/2/2021 - 1 samples'],
  ]
  expect(datasetsSection.find('DatasetSection').map(
      content => content.find('div').map(content => content.text())
  )).toEqual(datasets)

  expect(datasetsSection.find('DatasetSection').map(
      content => content.find('ButtonLink').map(content => content.text())
  )).toEqual([['Show 2 additional datasets'], [], []])
  const showMoreButton = datasetsSection.find('ButtonLink').first()
  showMoreButton.first().simulate('click')
  wrapper.update()

  const updatedDatasetsSection = wrapper.find('LoadingSection').filterWhere(
    content => content.find('b').first().text() === 'Exome Datasets',
  ).first().find('DatasetSection')
  expect(updatedDatasetsSection.find('ButtonLink').exists()).toBe(false)
  datasets[0].splice(2, 0, '1/2/2020 - 2 samples', '1/3/2020 - 2 samples')
  expect(updatedDatasetsSection.map(content => content.find('div').map(content => content.text()))).toEqual(datasets)
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

test('shows no submissions message when there are no mme submissions', () => {
  const noMmeState = cloneDeep(STATE_WITH_2_FAMILIES)
  noMmeState.projectsByGuid[PROJECT_GUID].mmeSubmissionCount = 0
  noMmeState.projectsByGuid[PROJECT_GUID].mmeDeletedSubmissionCount = 0

  const wrapper = renderProjectOverview(noMmeState)

  expect(wrapper.text()).toContain('No Submissions')
})

test('falls back to the raw sample type when it is not a recognized sample type', () => {
  const unknownSampleTypeState = cloneDeep(STATE_WITH_2_FAMILIES)
  unknownSampleTypeState.datasetsByGuid.DS_UNKNOWN = {
    datasetType: 'SNV_INDEL',
    sampleType: 'FOO',
    projectGuid: PROJECT_GUID,
    activeIndividuals: ['I021476_na19678_2'],
    inactiveIndividuals: [],
    loadedDate: '2019-01-01T12:00:00.000Z',
  }

  const wrapper = renderProjectOverview(unknownSampleTypeState)

  expect(wrapper.text()).toContain('FOO Datasets')
})

test('does not render the anvil section when there is no workspace and the user is not a pm', () => {
  const noAnvilState = cloneDeep(STATE_WITH_2_FAMILIES)
  noAnvilState.projectsByGuid[PROJECT_GUID].workspaceName = null
  noAnvilState.user.isPm = false
  noAnvilState.user.isAnvil = true

  const wrapper = renderProjectOverview(noAnvilState)

  expect(wrapper.find('[title="AnVIL Workspace"]').exists()).toBe(false)
})

test('renders "None" for the anvil workspace when the user is a pm with no workspace', () => {
  const noWorkspaceState = cloneDeep(STATE_WITH_2_FAMILIES)
  noWorkspaceState.projectsByGuid[PROJECT_GUID].workspaceName = null
  noWorkspaceState.user.isPm = true
  noWorkspaceState.user.isAnvil = true

  const wrapper = renderProjectOverview(noWorkspaceState)

  expect(wrapper.text()).toContain('AnVIL WorkspaceNone')
  expect(wrapper.find('[modalId="editAnvilWorkspace"]').exists()).toBe(true)
})

test('uses the analysis group workspace details when the group has its own workspace', () => {
  const analysisGroupState = cloneDeep(STATE_WITH_2_FAMILIES)
  analysisGroupState.user.isAnvil = true

  const wrapper = mount(
    <Provider store={configureStore([thunk])(analysisGroupState)}>
      <MemoryRouter>
        <ProjectOverview
          familiesLoading={false}
          overviewLoading={false}
          analysisGroupGuid="AG0000183_test_group"
        />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.text()).toContain('anvil-analysis-group')
})

test('shows a loading indicator when families or overview data is loading', () => {
  const wrapper = mount(
    <Provider store={configureStore([thunk])(STATE_WITH_2_FAMILIES)}>
      <MemoryRouter>
        <ProjectOverview familiesLoading overviewLoading />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.find('Dimmer').exists()).toBe(true)
  expect(wrapper.find('Loader').exists()).toBe(true)
})

import React from 'react'
import { mount, configure, shallow } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'
import CaseReviewTable from './CaseReview'

import { STATE_WITH_2_FAMILIES } from '../fixtures'

const CASE_REVIEW_STATUS_COUNTS = [
  {'color': '#2196F3', 'count': 4, 'name': 'In Review', 'value': 'I'},
  {'color': '#fddb28', 'count': 0, 'name': 'Uncertain', 'value': 'U'},
  {'color': '#8BC34A', 'count': 2, 'name': 'Accepted', 'value': 'A'},
  {'color': '#4f5cb3', 'count': 0, 'name': 'Not Accepted', 'value': 'R'},
  {'color': '#F44336', 'count': 0, 'name': 'More Info Needed', 'value': 'Q'},
  {'color': '#996699', 'count': 0, 'name': 'Pending Results and Records', 'value': 'P'},
  {'color': '#3827c1', 'count': 0, 'name': 'NMI Review', 'value': 'N'},
  {'color': '#990099', 'count': 0, 'name': 'Waitlist', 'value': 'W'},
  {'color': '#eb7f2f', 'count': 0, 'name': 'Lost To Follow-Up', 'value': 'L'},
  {'color': '#6c6d85', 'count': 0, 'name': 'Inactive', 'value': 'V'},
]

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

test('renders the accepted families and the individual status summary', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <CaseReviewTable />
      </MemoryRouter>
    </Provider>,
  )
  expect(wrapper.find('FamilyTableRow').length).toEqual(2)
  expect(wrapper.text()).toContain('Individual Statuses:')
  
  const headerStatus = wrapper.find('HorizontalStackedBar')
  expect(headerStatus.exists()).toBe(true)
  expect(headerStatus.prop('data')).toEqual(CASE_REVIEW_STATUS_COUNTS)

  // Export data is properly rendered
  const popupWrapper = shallow( wrapper.find('Popup[on="click"]').prop('content'))
  const caseReviewExportUrls = popupWrapper.root().prop('downloads')
  const familiesExport = caseReviewExportUrls.find(({ name }) => name === 'Families')
  expect(familiesExport.filename).toContain('case_review')
  const familiesData = familiesExport.getRawData(STATE_WITH_2_FAMILIES)
  const family2 = familiesData.find(f => f.familyGuid === 'F011652_2')
  const individualsExport = caseReviewExportUrls.find(({ name }) => name === 'Individuals')
  const individualsData = individualsExport.getRawData(STATE_WITH_2_FAMILIES)
  expect(individualsData.length).toEqual(6)
  const individual = individualsData.find(i => i.individualGuid === 'I021475_na19675_1')
  expect(individualsExport.processRow(individual)).toEqual([
    '1', 'NA19675', undefined, undefined, 'Male', 'Affected', '', 'No',
    'HP:0001324 (Muscle weakness)', 'HP:0001631 (Defect in the atrial septum)', 'In Review',
    '2016-12-05T10:29:00.000Z', 'test user', '',
  ])

  const row = familiesExport.processRow(family2)
  // F011652_2 has no internal case review summary/notes set, so stripMarkdown falls back to ''
  expect(row[row.length - 2]).toEqual('')
  expect(row[row.length - 1]).toEqual('')
})

test('case review status counts exclude individuals belonging to a different project', () => {
  const otherProjectState = {
    ...STATE_WITH_2_FAMILIES,
    individualsByGuid: {
      ...STATE_WITH_2_FAMILIES.individualsByGuid,
      I_OTHER_PROJECT: {
        ...STATE_WITH_2_FAMILIES.individualsByGuid.I021475_na19675_1,
        individualGuid: 'I_OTHER_PROJECT',
        projectGuid: 'R_SOME_OTHER_PROJECT',
        caseReviewStatus: 'A',
      },
    },
  }

  const wrapper = mount(
    <Provider store={configureStore(otherProjectState)}>
      <MemoryRouter>
        <CaseReviewTable />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.find('HorizontalStackedBar').prop('data')).toEqual(CASE_REVIEW_STATUS_COUNTS)
})

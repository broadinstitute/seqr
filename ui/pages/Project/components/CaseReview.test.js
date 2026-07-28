import React from 'react'
import {mount, configure, shallow} from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'
import CaseReviewTable from './CaseReview'

import { getCaseReviewStatusCounts } from '../selectors' // TODO
import { STATE_WITH_2_FAMILIES } from '../fixtures'

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

  expect(wrapper.find('HorizontalStackedBar').exists()).toBe(true)
  expect(wrapper.text()).toContain('Individual Statuses:')
  expect(wrapper.find('FamilyTableRow').length).toEqual(2)

  // Export data is properly rendered
  const popupWrapper = shallow( wrapper.find('Popup[on="click"]').prop('content'))
  const caseReviewExportUrls = popupWrapper.root().prop('downloads')
  const familiesExport = caseReviewExportUrls.find(({ name }) => name === 'Families')
  expect(familiesExport.filename).toContain('case_review')
  const familiesData = familiesExport.getRawData(STATE_WITH_2_FAMILIES)
  const family2 = familiesData.find(f => f.familyGuid === 'F011652_2')

  const row = familiesExport.processRow(family2)
  // F011652_2 has no internal case review summary/notes set, so stripMarkdown falls back to ''
  expect(row[row.length - 2]).toEqual('')
  expect(row[row.length - 1]).toEqual('')
})

test('getCaseReviewStatusCounts excludes individuals belonging to a different project', () => {
  const baseCounts = getCaseReviewStatusCounts(STATE_WITH_2_FAMILIES)
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

  const updatedCounts = getCaseReviewStatusCounts(otherProjectState)

  expect(updatedCounts).toEqual(baseCounts)
})

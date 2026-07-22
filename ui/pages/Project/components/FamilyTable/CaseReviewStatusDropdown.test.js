import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'
import { getIndividualsByGuid } from 'redux/selectors'
import { updateIndividual } from 'redux/rootReducer'
import CaseReviewStatusDropdown, { CaseReviewStatusDropdownComponent } from './CaseReviewStatusDropdown'

import { STATE1, STATE_WITH_2_FAMILIES } from '../../fixtures'

jest.mock('redux/rootReducer', () => ({
  ...jest.requireActual('redux/rootReducer'),
  updateIndividual: jest.fn(values => ({ type: 'MOCK_UPDATE_INDIVIDUAL', values })),
}))

configure({ adapter: new Adapter() })

const renderDropdown = props => mount(
  <Provider store={configureStore()(STATE_WITH_2_FAMILIES)}>
    <CaseReviewStatusDropdownComponent {...props} />
  </Provider>,
)

test('renders the current case review status and no discussion field when more info is not needed', () => {
  const individual = Object.values(getIndividualsByGuid(STATE1))[0]
  const props = {
    individual,
    updateIndividualField: () => () => {},
    updateIndividualDiscussion: () => {},
  }

  const wrapper = renderDropdown(props)

  expect(wrapper.find('Dropdown').find('.text').first().text()).toEqual('In Review')
  expect(wrapper.find({ field: 'caseReviewDiscussion' }).exists()).toBe(false)
})

test('renders a discussion field when more info is needed', () => {
  const individual = { ...Object.values(getIndividualsByGuid(STATE1))[0], caseReviewStatus: 'Q' }
  const props = {
    individual,
    updateIndividualField: () => () => {},
    updateIndividualDiscussion: () => {},
  }

  const wrapper = renderDropdown(props)

  expect(wrapper.find('Dropdown').find('.text').first().text()).toEqual('More Info Needed')
  const discussionField = wrapper.find({ field: 'caseReviewDiscussion' }).first()
  expect(discussionField.exists()).toBe(true)
  expect(discussionField.prop('modalTitle')).toEqual(`${individual.displayName}: Case Review Discussion`)
})

test('dispatches updateIndividual actions via mapDispatchToProps', () => {
  const individual = Object.values(getIndividualsByGuid(STATE1))[0]
  const store = configureStore()(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <CaseReviewStatusDropdown individual={individual} />
    </Provider>,
  )

  const { updateIndividualField, updateIndividualDiscussion } = wrapper.find(CaseReviewStatusDropdownComponent).props()

  updateIndividualField('caseReviewStatus')('E')
  updateIndividualDiscussion({ caseReviewDiscussion: 'Some notes' })

  expect(updateIndividual).toHaveBeenCalledTimes(2)
  expect(updateIndividual).toHaveBeenCalledWith({
    individualGuid: individual.individualGuid,
    individualField: 'case_review_status',
    caseReviewStatus: 'E',
  })
  expect(updateIndividual).toHaveBeenCalledWith({
    individualGuid: individual.individualGuid,
    individualField: 'case_review_discussion',
    caseReviewDiscussion: 'Some notes',
  })

  const actions = store.getActions()
  expect(actions).toContainEqual({
    type: 'MOCK_UPDATE_INDIVIDUAL',
    values: {
      individualGuid: individual.individualGuid,
      individualField: 'case_review_status',
      caseReviewStatus: 'E',
    },
  })
})

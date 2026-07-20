import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import { Provider } from 'react-redux'
import { FAMILY_FIELD_ID } from 'shared/utils/constants'
import { TableHeaderRowComponent } from './TableHeaderRow'

import { STATE_WITH_2_FAMILIES } from '../../../fixtures'

configure({ adapter: new Adapter() })

const noOp = () => {}
const updateFamiliesTableField = () => noOp

const renderHeaderRow = props => mount(
  <Provider store={configureStore()(STATE_WITH_2_FAMILIES)}>
    <table>
      <TableHeaderRowComponent
        familiesTableState={STATE_WITH_2_FAMILIES.familyTableState}
        updateFamiliesTableField={updateFamiliesTableField}
        {...props}
      />
    </table>
  </Provider>,
)

const headerText = wrapper => wrapper.find('th').first().text()
  .replace(/\s+/g, ' ')
  .trim()

test('renders the visible/total family count and search filter', () => {
  const wrapper = renderHeaderRow({ visibleFamiliesCount: 1, totalFamiliesCount: 2 })

  expect(headerText(wrapper)).toEqual('Showing 1 out of 2 families')
  expect(wrapper.find('input[placeholder="Search..."]').exists()).toBe(true)
})

test('renders all families when the visible count matches the total count', () => {
  const wrapper = renderHeaderRow({ visibleFamiliesCount: 2, totalFamiliesCount: 2 })

  expect(headerText(wrapper)).toEqual('Showing all 2 families')
})

test('renders a FamilyLayout row when fields are specified', () => {
  const wrapper = renderHeaderRow({
    visibleFamiliesCount: 2,
    totalFamiliesCount: 2,
    fields: [{ id: FAMILY_FIELD_ID }],
  })

  const familyLayout = wrapper.find({ compact: true, fields: [{ id: FAMILY_FIELD_ID }] })
  expect(familyLayout.exists()).toBe(true)
})

import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import SortDirectionToggle from './SortDirectionToggle'
import { getFamiliesSortDirection } from '../../../selectors'

import { STATE1 } from '../../../fixtures'

configure({ adapter: new Adapter() })

test('renders the sort direction icon and toggles direction on click', () => {
  const onChange = jest.fn()
  const props = {
    value: getFamiliesSortDirection(STATE1),
    onChange,
  }

  const wrapper = mount(<SortDirectionToggle {...props} />)

  expect(wrapper.find('Icon').prop('name')).toEqual('arrow up')

  wrapper.find('button').simulate('click')

  expect(onChange).toHaveBeenCalledWith(1)
})

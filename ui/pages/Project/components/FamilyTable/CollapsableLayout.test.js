import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'

import CollapsableLayout from './CollapsableLayout'

configure({ adapter: new Adapter() })

const LayoutComponent = ({ fields, compact, disableEdit, toggleDetails }) => (
  <div>
    <span className="fieldCount">{fields.length}</span>
    <span className="compact">{compact ? 'compact' : 'full'}</span>
    <span className="disableEdit">{disableEdit ? 'disabled' : 'enabled'}</span>
    {toggleDetails && <button type="button" onClick={toggleDetails}>Toggle</button>}
  </div>
)

test('renders in compact mode with noDetailFields when collapsed by default', () => {
  const props = {
    layoutComponent: LayoutComponent,
    detailFields: [{ name: 'a' }, { name: 'b' }, { name: 'c' }],
    noDetailFields: [{ name: 'a' }],
  }

  const wrapper = mount(<CollapsableLayout {...props} />)

  expect(wrapper.find('.fieldCount').text()).toEqual('1')
  expect(wrapper.find('.compact').text()).toEqual('compact')
  expect(wrapper.find('.disableEdit').text()).toEqual('disabled')
  expect(wrapper.find('button').exists()).toBe(true)
})

test('toggles to show detailFields when toggle is clicked', () => {
  const props = {
    layoutComponent: LayoutComponent,
    detailFields: [{ name: 'a' }, { name: 'b' }, { name: 'c' }],
    noDetailFields: [{ name: 'a' }],
  }

  const wrapper = mount(<CollapsableLayout {...props} />)

  wrapper.find('button').simulate('click')
  wrapper.update()

  expect(wrapper.find('.fieldCount').text()).toEqual('3')
  expect(wrapper.find('.compact').text()).toEqual('full')
  expect(wrapper.find('.disableEdit').text()).toEqual('enabled')
})

test('does not allow toggle when noDetailFields is not provided', () => {
  const props = {
    layoutComponent: LayoutComponent,
    detailFields: [{ name: 'a' }, { name: 'b' }],
  }

  const wrapper = mount(<CollapsableLayout {...props} />)

  expect(wrapper.find('.fieldCount').text()).toEqual('2')
  expect(wrapper.find('.compact').text()).toEqual('full')
  expect(wrapper.find('button').exists()).toBe(false)
})
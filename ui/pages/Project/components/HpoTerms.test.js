import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import { Form as FinalForm } from 'react-final-form'

import { HPO_FORM_FIELDS } from './HpoTerms'

configure({ adapter: new Adapter() })

const { component: HpoTermsEditor } = HPO_FORM_FIELDS.find(({ name }) => name === 'features')

const FEATURES = [
  { index: 0, id: 'HP:0001250', label: 'Seizures' },
  { index: 1, id: 'HP:0001252', label: 'Hypotonia' },
]

test('renders each feature with its label and id', () => {
  const wrapper = mount(
    <HpoTermsEditor name="features" value={FEATURES} onChange={jest.fn()} allowAdditions />
  )

  expect(wrapper.find('Icon[name="remove"]').length).toEqual(2)
  expect(wrapper.text()).toContain('Seizures (HP:0001250)')
  expect(wrapper.text()).toContain('Hypotonia (HP:0001252)')
  expect(wrapper.find('ButtonLink[content="Add Feature"]').exists()).toBe(true)
})

test('removes a feature when its remove icon is clicked', () => {
  const onChange = jest.fn()
  const wrapper = mount(
    <HpoTermsEditor name="features" value={FEATURES} onChange={onChange} allowAdditions />
  )

  wrapper.find('Icon[id="HP:0001250"]').simulate('click')

  expect(onChange).toHaveBeenCalledWith([FEATURES[1]])
})

test('toggles feature details when Edit Details is clicked', () => {
  // The details section renders a react-final-form Field, so it needs a surrounding Form
  const wrapper = mount(
    <FinalForm
      onSubmit={() => {}}
      render={() => (
        <HpoTermsEditor name="features" value={FEATURES} onChange={jest.fn()} allowAdditions />
      )}
    />
  )

  expect(wrapper.find('input[name="features[0].notes"]').exists()).toBe(false)

  wrapper.find('ButtonLink[content="Edit Details"]').at(0).find('button').simulate('click')
  wrapper.update()

  expect(wrapper.find('input[name="features[0].notes"]').exists()).toBe(true)
  expect(wrapper.find('ButtonLink[content="Hide Details"]').exists()).toBe(true)
})

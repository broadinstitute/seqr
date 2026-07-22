import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import { Form as FinalForm } from 'react-final-form'
import configureStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'

import { HPO_FORM_FIELDS } from './HpoTerms'

jest.mock('redux/rootReducer', () => ({
  ...jest.requireActual('redux/rootReducer'),
  loadHpoTerms: () => ({ type: 'NOOP' }),
}))

configure({ adapter: new Adapter() })

const mockStore = configureStore([thunk])

const { component: HpoTermsEditor } = HPO_FORM_FIELDS.find(({ name }) => name === 'features')
const { component: NonstandardHpoTermsEditor, format: formatNonstandard } = HPO_FORM_FIELDS.find(
  ({ name }) => name === 'nonstandardFeatures',
)
const { format: formatFeatures } = HPO_FORM_FIELDS.find(({ name }) => name === 'features')
const { component: AbsentHpoTermsEditor, format: formatAbsent } = HPO_FORM_FIELDS.find(
  ({ name }) => name === 'absentFeatures',
)
const { format: formatAbsentNonstandard } = HPO_FORM_FIELDS.find(
  ({ name }) => name === 'absentNonstandardFeatures',
)

const FEATURES = [
  { index: 0, id: 'HP:0001250', label: 'Seizures' },
  { index: 1, id: 'HP:0001252', label: 'Hypotonia' },
]

test('renders each feature with its label and id', () => {
  const wrapper = mount(
    <HpoTermsEditor name="features" value={FEATURES} onChange={jest.fn()} allowAdditions />,
  )

  expect(wrapper.find('Icon[name="remove"]').length).toEqual(2)
  expect(wrapper.text()).toContain('Seizures (HP:0001250)')
  expect(wrapper.text()).toContain('Hypotonia (HP:0001252)')
  expect(wrapper.find('ButtonLink[content="Add Feature"]').exists()).toBe(true)
})

test('removes a feature when its remove icon is clicked', () => {
  const onChange = jest.fn()
  const wrapper = mount(
    <HpoTermsEditor name="features" value={FEATURES} onChange={onChange} allowAdditions />,
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
    />,
  )

  expect(wrapper.find('input[name="features[0].notes"]').exists()).toBe(false)

  wrapper.find('ButtonLink[content="Edit Details"]').at(0).find('button').simulate('click')
  wrapper.update()

  expect(wrapper.find('input[name="features[0].notes"]').exists()).toBe(true)
  expect(wrapper.find('ButtonLink[content="Hide Details"]').exists()).toBe(true)
})

test('formats standard features into a flattened list with category headers', () => {
  const result = formatFeatures([
    { id: 'HP:0001250', label: 'Seizures', category: 'HP:0000707' },
    { id: 'HP:0001252', label: 'Hypotonia', category: 'HP:0000707' },
  ])

  expect(result).toEqual([
    { id: 'HP:0001250', label: 'Seizures', category: 'HP:0000707', index: 0, categoryName: 'Nervous System' },
    { id: 'HP:0001252', label: 'Hypotonia', category: 'HP:0000707', index: 1 },
  ])
})

test('formats nonstandard features into a flattened list with category headers', () => {
  const result = formatNonstandard([
    { id: 'x1', label: 'Custom term', categories: [{ id: 'HP:0000924', label: 'Skeletal' }] },
  ])

  expect(result).toEqual([
    {
      id: 'x1',
      label: 'Custom term',
      categories: [{ id: 'HP:0000924', label: 'Skeletal' }],
      index: 0,
      categoryName: 'Skeletal',
    },
  ])
})

test('renders a section header and category name for non-additive editors', () => {
  const formatted = formatAbsent([{ id: 'HP:0001250', label: 'Seizures', category: 'HP:0000707' }])
  const wrapper = mount(
    <AbsentHpoTermsEditor
      name="absentFeatures"
      value={formatted}
      onChange={jest.fn()}
      header={{ content: 'Not Present', color: 'red' }}
    />,
  )

  expect(wrapper.find('Header[content="Not Present"]').exists()).toBe(true)
  expect(wrapper.find('Header[content="Nervous System"]').exists()).toBe(true)
  expect(wrapper.find('ButtonLink[content="Add Feature"]').exists()).toBe(false)
})

test('formats absent nonstandard features into a flattened list with category headers', () => {
  const result = formatAbsentNonstandard([
    { id: 'x2', label: 'Custom absent term', categories: [{ id: 'HP:0000598', label: 'Ear' }] },
  ])

  expect(result).toEqual([
    {
      id: 'x2',
      label: 'Custom absent term',
      categories: [{ id: 'HP:0000598', label: 'Ear' }],
      index: 0,
      categoryName: 'Ear',
    },
  ])
})

test('renders a green header for nonstandard present features', () => {
  const formatted = formatNonstandard([
    { id: 'x1', label: 'Custom term', categories: [{ id: 'HP:0000924', label: 'Skeletal' }] },
  ])
  const wrapper = mount(
    <NonstandardHpoTermsEditor
      name="nonstandardFeatures"
      value={formatted}
      onChange={jest.fn()}
      header={{ content: 'Present', color: 'green' }}
    />,
  )

  expect(wrapper.find('Header[content="Present"]').exists()).toBe(true)
  expect(wrapper.text()).toContain('Custom term')
})

test('does not add a duplicate feature', () => {
  const onChange = jest.fn()
  const wrapper = mount(
    <HpoTermsEditor name="features" value={FEATURES} onChange={onChange} allowAdditions />,
  )

  wrapper.find(HpoTermsEditor).instance().addItem({ id: 'HP:0001250', label: 'Seizures' })

  expect(onChange).not.toHaveBeenCalled()
})

test('toggles the add-item selector when Add Feature is clicked', () => {
  const store = mockStore({ hpoTermsByParent: {}, hpoTermsLoading: { isLoading: false } })
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <HpoTermsEditor name="features" value={FEATURES} onChange={jest.fn()} allowAdditions />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.find('AwesomeBar').exists()).toBe(false)

  wrapper.find('ButtonLink[content="Add Feature"]').find('button').simulate('click')
  wrapper.update()

  expect(wrapper.find('AwesomeBar').exists()).toBe(true)
  expect(wrapper.find('ButtonLink[content="Add Feature"]').exists()).toBe(false)
})

test('adds a feature selected from a loaded HPO category', () => {
  const store = mockStore({
    hpoTermsByParent: { 'HP:0000707': { 'HP:0009999': { id: 'HP:0009999', label: 'New Term' } } },
    hpoTermsLoading: { isLoading: false },
  })
  const onChange = jest.fn()
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <HpoTermsEditor name="features" value={FEATURES} onChange={onChange} allowAdditions />
      </MemoryRouter>
    </Provider>,
  )

  wrapper.find('ButtonLink[content="Add Feature"]').find('button').simulate('click')
  wrapper.update()

  wrapper.findWhere(n => n.type() === 'a' && n.text() === 'Nervous System').first().simulate('click')
  wrapper.update()

  expect(wrapper.text()).toContain('New Term')

  wrapper.find('Icon[name="plus"]').simulate('click')

  expect(onChange).toHaveBeenCalledWith([...FEATURES, { id: 'HP:0009999', label: 'New Term' }])
})

test('formats an empty/ missing feature list as an empty array', () => {
  expect(formatFeatures(undefined)).toEqual([])
})

test('parses qualifiers back into a lookup keyed by type', () => {
  const wrapper = mount(
    <FinalForm
      onSubmit={() => {}}
      render={() => (
        <HpoTermsEditor name="features" value={FEATURES} onChange={jest.fn()} allowAdditions />
      )}
    />,
  )

  wrapper.find('ButtonLink[content="Edit Details"]').at(0).find('button').simulate('click')
  wrapper.update()

  const qualifiersField = wrapper.find('ForwardRef(Field)[name="features[0].qualifiers"]')
  expect(qualifiersField.exists()).toBe(true)
  const { parse } = qualifiersField.props()

  expect(parse({ severity: 'Mild' })).toEqual([{ type: 'severity', label: 'Mild' }])
  expect(parse(undefined)).toEqual([])
})

test('renders the hpo id alone when a feature has no label', () => {
  const unlabeledFeature = [{ index: 0, id: 'HP:0000001' }]
  const wrapper = mount(
    <HpoTermsEditor name="features" value={unlabeledFeature} onChange={jest.fn()} allowAdditions />,
  )

  expect(wrapper.text()).toContain('HP:0000001')
  expect(wrapper.text()).not.toContain('undefined')
})

test('does not render any terms when the loaded category has no terms', () => {
  const store = mockStore({
    hpoTermsByParent: { 'HP:0000598': {} },
    hpoTermsLoading: { isLoading: false },
  })
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <HpoTermsEditor name="features" value={FEATURES} onChange={jest.fn()} allowAdditions />
      </MemoryRouter>
    </Provider>,
  )

  wrapper.find('ButtonLink[content="Add Feature"]').find('button').simulate('click')
  wrapper.update()

  wrapper.findWhere(n => n.type() === 'a' && n.text() === 'Ear').first().simulate('click')
  wrapper.update()

  expect(wrapper.find('Tab.Pane').exists()).toBe(false)
})

test('formats existing qualifiers into a lookup keyed by type', () => {
  const wrapper = mount(
    <FinalForm
      onSubmit={() => {}}
      render={() => (
        <HpoTermsEditor name="features" value={FEATURES} onChange={jest.fn()} allowAdditions />
      )}
    />,
  )

  wrapper.find('ButtonLink[content="Edit Details"]').at(0).find('button').simulate('click')
  wrapper.update()

  const qualifiersField = wrapper.find('ForwardRef(Field)[name="features[0].qualifiers"]')
  const { format } = qualifiersField.props()

  expect(format([{ type: 'severity', label: 'Mild' }])).toEqual({ severity: 'Mild' })
})

test('updates a qualifier value when a radio option is selected', () => {
  const wrapper = mount(
    <FinalForm
      onSubmit={() => {}}
      render={() => (
        <HpoTermsEditor name="features" value={FEATURES} onChange={jest.fn()} allowAdditions />
      )}
    />,
  )

  wrapper.find('ButtonLink[content="Edit Details"]').at(0).find('button').simulate('click')
  wrapper.update()

  wrapper.find('AccordionTitle').filterWhere(n => n.text() === 'Severity').first().simulate('click')
  wrapper.update()

  const moderateRadio = wrapper.find('Radio').filterWhere(n => n.prop('label') === 'Moderate')
  expect(moderateRadio.prop('checked')).toBe(false)

  moderateRadio.prop('onChange')({}, { checked: true })
  wrapper.update()

  expect(wrapper.find('Radio').filterWhere(n => n.prop('label') === 'Moderate').prop('checked')).toBe(true)
})

test('parses a selected hpo search result into an item to add', () => {
  const store = mockStore({
    hpoTermsByParent: {},
    hpoTermsLoading: { isLoading: false },
  })
  const onChange = jest.fn()
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <HpoTermsEditor name="features" value={FEATURES} onChange={onChange} allowAdditions />
      </MemoryRouter>
    </Provider>,
  )

  wrapper.find('ButtonLink[content="Add Feature"]').find('button').simulate('click')
  wrapper.update()

  wrapper.find('AwesomeBar').instance().handleResultSelect(
    { preventDefault: () => {} },
    { result: { key: 'HP:0005678', title: 'Ataxia', category: 'HP:0000707' } },
  )

  expect(onChange).toHaveBeenCalledWith([...FEATURES, { id: 'HP:0005678', label: 'Ataxia', category: 'HP:0000707' }])
})

test('renders the nested category tab when a term is selected', () => {
  const store = mockStore({
    hpoTermsByParent: {
      'HP:0000707': { 'HP:0009999': { id: 'HP:0009999', label: 'New Term' } },
    },
    hpoTermsLoading: { isLoading: false },
  })
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <HpoTermsEditor name="features" value={FEATURES} onChange={jest.fn()} allowAdditions />
      </MemoryRouter>
    </Provider>,
  )

  wrapper.find('ButtonLink[content="Add Feature"]').find('button').simulate('click')
  wrapper.update()

  wrapper.findWhere(n => n.type() === 'a' && n.text() === 'Nervous System').first().simulate('click')
  wrapper.update()

  wrapper.findWhere(n => n.type() === 'a' && n.text().includes('New Term')).first().simulate('click')
  wrapper.update()

  expect(wrapper.find('DataLoader').filterWhere(n => n.prop('contentId') === 'HP:0009999').exists()).toBe(true)
})

test('checks whether hpo terms are loading when none are cached for the category', () => {
  const store = mockStore({
    hpoTermsByParent: {},
    hpoTermsLoading: { isLoading: true },
  })
  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <HpoTermsEditor name="features" value={FEATURES} onChange={jest.fn()} allowAdditions />
      </MemoryRouter>
    </Provider>,
  )

  wrapper.find('ButtonLink[content="Add Feature"]').find('button').simulate('click')
  wrapper.update()

  wrapper.findWhere(n => n.type() === 'a' && n.text() === 'Ear').first().simulate('click')
  wrapper.update()

  expect(wrapper.find('Dimmer').exists()).toBe(true)
})

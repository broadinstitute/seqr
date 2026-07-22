import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import { STATE_WITH_2_FAMILIES } from '../fixtures'
import Matchmaker from './Matchmaker'

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

const MATCH = { params: { familyGuid: 'F011652_2' } }
const MATCH_CREATE_SUBMISSION = { params: { familyGuid: 'F011652_1' } }

test('renders the affected individual with no matchmaker submission', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  const wrapper = mount(
    <Provider store={store}>
      <Matchmaker match={MATCH} />
    </Provider>,
  )

  expect(wrapper.find('Header[content="This individual has no submissions"]').exists()).toBe(true)
  expect(wrapper.find('ButtonLink[content="Submit to Matchmaker"]').exists()).toBe(true)
})

test('opens the create submission modal and exercises form field callbacks', () => {
  const store = configureStore({
    ...STATE_WITH_2_FAMILIES,
    savedVariantFamilies: { F011652_2: { loaded: true } },
    modal: { 'I021475_na19675_2_-_CreateMmeSubmission': { open: true } },
  })

  const wrapper = mount(
    <Provider store={store}>
      <Matchmaker match={MATCH} />
    </Provider>,
  )

  const contactsField = wrapper.find('ForwardRef(Field)[name="contacts[0]"]')
  expect(contactsField.exists()).toBe(true)
  const validateContacts = contactsField.first().prop('validate')
  expect(validateContacts({ email: 'not-an-email' })).toBe('Invalid email')
  expect(validateContacts({ email: 'test@test.com' })).toBeUndefined()

  const geneVariantsField = wrapper.find('ForwardRef(Field)[name="geneVariants"]')
  expect(geneVariantsField.exists()).toBe(true)
  expect(geneVariantsField.prop('parse')({ a: { variantGuid: 'a' }, b: false })).toEqual([{ variantGuid: 'a' }])
  expect(geneVariantsField.prop('format')([
    { variantGuid: 'SV1', geneId: 'ENSG1' },
  ])).toEqual({ 'SV1-ENSG1': { variantGuid: 'SV1', geneId: 'ENSG1' } })

  const phenotypesField = wrapper.find('ForwardRef(Field)[name="phenotypes"]')
  expect(phenotypesField.exists()).toBe(true)
  expect(phenotypesField.prop('format')([{ id: 'HP:0001324' }])).toEqual({ 'HP:0001324': true })
  expect(phenotypesField.prop('validate')([], { geneVariants: [] })).toBe(
    'Genotypes and/or phenotypes are required',
  )
  expect(phenotypesField.prop('validate')([{ id: 'HP:0001324' }], { geneVariants: [] })).toBeUndefined()

  const phenotypesTable = wrapper.find({ idField: 'id' })
  expect(phenotypesTable.exists()).toBe(true)
  phenotypesTable.first().prop('onChange')({ 'HP:0001324': true })

  const genotypesTable = wrapper.find({ idField: 'variantId' })
  expect(genotypesTable.exists()).toBe(true)
})

test('renders the affected individual with a matchmaker submission', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  const wrapper = mount(
    <Provider store={store}>
      <Matchmaker match={MATCH_CREATE_SUBMISSION} />
    </Provider>,
  )

  expect(wrapper.find('Header[content="This individual has no submissions"]').exists()).toBe(false)
  expect(wrapper.find('ButtonLink[content="Search for New Matches"]').exists()).toBe(true)
  expect(wrapper.find('ButtonLink[content="Update Submission"]').exists()).toBe(true)
  expect(wrapper.find('ButtonLink[content="Delete Submission"]').exists()).toBe(true)

  expect(wrapper.find('Header[content="Previous Matches"]').exists()).toBe(true)

  const wrapperText = wrapper.text()
  expect(wrapperText).toContain('Childhood Psychiatric Disorder Candidate Genes')
  expect(wrapperText).toContain('James Crowley')
  expect(wrapperText).toContain('2016-174')
  expect(wrapperText).toContain('Janneke Weiss')

  const idColumn = wrapper.find('DataTable').first().prop('columns').find(({ name }) => name === 'id')
  expect(idColumn.format({ id: 'p1', patient: { label: 'A Label' } }, true)).toBe('A Label')
  const withOriginatingSubmission = idColumn.format({
    id: 'p1',
    patient: { disorders: [{ id: 'MONDO:1' }, { id: 'MONDO:2' }] },
    originatingSubmission: { projectGuid: 'R0237_1000_genomes_demo', familyGuid: 'F011652_1' },
  }, false)
  expect(withOriginatingSubmission.props.trigger.props.children[0].props.to).toBe(
    '/project/R0237_1000_genomes_demo/family_page/F011652_1/matchmaker_exchange',
  )
  expect(withOriginatingSubmission.props.content.some(({ key }) => key === 'disorders')).toBe(true)

  store.clearActions()
  const { searchMme, onSubmit } = wrapper.findWhere(
    n => n.props().searchMme && n.props().onSubmit,
  ).first().props()
  searchMme()
  expect(store.getActions().some(({ type }) => type === 'REQUEST_MME_MATCHES')).toBe(true)
  expect(() => onSubmit({ comments: 'updated' })).not.toThrow()
})

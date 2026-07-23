import React from 'react'
import { mount, shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { STATE_WITH_2_FAMILIES } from '../fixtures'
import Matchmaker from './Matchmaker'

jest.mock('shared/utils/httpRequestHelper', () => ({
  ...jest.requireActual('shared/utils/httpRequestHelper'),
  HttpRequestHelper: jest.fn().mockImplementation(() => ({
    get: jest.fn(() => Promise.resolve()),
    post: jest.fn(() => Promise.resolve()),
  })),
}))

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

beforeEach(() => {
  HttpRequestHelper.mockClear()
})

const MATCH = { params: { familyGuid: 'F011652_2' } }
const MATCH_CREATE_SUBMISSION = { params: { familyGuid: 'F011652_1' } }
const MATCH_UNKNOWN_FAMILY = { params: { familyGuid: 'F_UNKNOWN' } }
const FAILED_CONTACT_META = { submitFailed: true, error: 'Invalid email' }
const NOT_FAILED_CONTACT_META = { submitFailed: false, error: 'Invalid email' }
const INDIVIDUAL_WITH_FEATURES = {
  features: [
    { id: 'HP:0001324', label: 'Muscle weakness' },
    { id: 'HP:0001631', label: 'Defect in the atrial septum', observed: 'no' },
    { id: 'HP:0009821', label: 'Forearm undergrowth' },
  ],
}
const EMPTY_VALUE = {}

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
  expect(validateContacts({})).toBe('Invalid email')
  expect(validateContacts()).toBe('Invalid email')

  // ContactFieldItem is a plain function component rendered as an itemComponent, so it can be
  // shallow rendered directly with custom meta to exercise the submitFailed error branch
  const ContactFieldItem = wrapper.find('ContactFieldItem').first().type()
  const failedContactItem = shallow(
    <ContactFieldItem icon={<i />} name="contacts[0]" meta={FAILED_CONTACT_META} />,
  )
  expect(failedContactItem.find({ name: 'contacts[0].email' }).prop('error')).toBe('Invalid email')
  const notFailedContactItem = shallow(
    <ContactFieldItem icon={<i />} name="contacts[0]" meta={NOT_FAILED_CONTACT_META} />,
  )
  expect(notFailedContactItem.find({ name: 'contacts[0].email' }).prop('error')).toBeFalsy()

  const geneVariantsField = wrapper.find('ForwardRef(Field)[name="geneVariants"]')
  expect(geneVariantsField.exists()).toBe(true)
  expect(geneVariantsField.prop('parse')({ a: { variantGuid: 'a' }, b: false })).toEqual([{ variantGuid: 'a' }])
  expect(geneVariantsField.prop('parse')()).toEqual([])
  expect(geneVariantsField.prop('format')([
    { variantGuid: 'SV1', geneId: 'ENSG1' },
  ])).toEqual({ 'SV1-ENSG1': { variantGuid: 'SV1', geneId: 'ENSG1' } })
  expect(geneVariantsField.prop('format')()).toEqual({})

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

  const genotypeColumns = genotypesTable.first().prop('columns')
  const xposColumn = genotypeColumns.find(({ name }) => name === 'xpos')
  expect(xposColumn.format({ chrom: '1', pos: 12345, alt: 'A', ref: 'C' })).toBe('1:12345 C > A')
  expect(xposColumn.format({ chrom: '1', pos: 12345, end: 12350 })).toBe('1:12345-12350')
  const numAltColumn = genotypeColumns.find(({ name }) => name === 'numAlt')
  expect(numAltColumn.format({ numAlt: 2 })).toBeTruthy()
  const tagsColumn = genotypeColumns.find(({ name }) => name === 'tags')
  expect(tagsColumn.format({ tags: [{ tagGuid: 't1', color: 'red', name: 'Tag 1' }] }).length).toBe(1)
})

test('computes individual features onChange for the phenotypes edit table', () => {
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

  // BaseEditPhenotypesTable is not exported, so it is pulled off the mounted tree, the same way
  // ContactFieldItem is above, to exercise its onChange logic directly with custom individual data
  const phenotypesTable = wrapper.find({ idField: 'id' }).first()
  const BaseEditPhenotypesTable = phenotypesTable.parents().filterWhere(
    n => n.props().individual && n.props().onChange,
  ).first().type()

  const onChange = jest.fn()
  const editTable = shallow(
    <BaseEditPhenotypesTable individual={INDIVIDUAL_WITH_FEATURES} value={EMPTY_VALUE} onChange={onChange} />,
  )

  // selecting a subset filters out unselected features, defaults newly selected features to
  // "observed", and preserves an already-set observed value instead of overwriting it
  editTable.find({ idField: 'id' }).prop('onChange')({ 'HP:0001324': true, 'HP:0001631': true })
  expect(onChange).toHaveBeenCalledWith([
    { id: 'HP:0001324', label: 'Muscle weakness', observed: 'yes' },
    { id: 'HP:0001631', label: 'Defect in the atrial septum', observed: 'no' },
  ])

  onChange.mockClear()
  editTable.find({ idField: 'id' }).prop('onChange')({})
  expect(onChange).toHaveBeenCalledWith([])
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

  const columns = wrapper.find('DataTable').first().prop('columns')
  const idColumn = columns.find(({ name }) => name === 'id')
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
  // patient with only core fields and no label has no extra fields to display in a popup
  const noExtraFields = idColumn.format({ id: 'match1', patient: { id: 'p1' } }, false)
  expect(noExtraFields.type.displayName || noExtraFields.type).not.toBe('Popup')

  const contactColumn = columns.find(({ name }) => name === 'contact')
  expect(contactColumn.format({ patient: {} }, false)).toBeFalsy()
  expect(contactColumn.format({ patient: { contact: { institution: 'Inst', name: 'Name' } } }, true)).toBe('Inst')
  expect(contactColumn.format({ patient: { contact: { name: 'Name' } } }, true)).toBe('Name')
  expect(() => contactColumn.format({
    patient: { contact: { institution: 'Inst', name: 'Name', email: 'mailto:x@y.com', href: 'mailto:x@y.com' } },
  }, false)).not.toThrow()

  const geneVariantsColumn = columns.find(({ name }) => name === 'geneVariants')
  expect(geneVariantsColumn.format({ weContacted: true }, true)).toBe('Yes')
  const phenotypesColumn = columns.find(({ name }) => name === 'phenotypes')
  expect(phenotypesColumn.format({ hostContacted: false }, true)).toBe('No')
  const commentsColumn = columns.find(({ name }) => name === 'comments')
  expect(commentsColumn.format({ comments: 'a comment' }, true)).toBe('a comment')

  const fieldDisplay = wrapper.find({ field: 'matchStatus' }).first().prop('fieldDisplay')
  const notContacted = fieldDisplay({
    hostContacted: false, weContacted: false, flagForAnalysis: false, deemedIrrelevant: false, comments: '',
  })
  expect(notContacted.props.children[0].props.content).toBe('Not Contacted')
  expect(notContacted.props.children[0].props.color).toBe('orange')
  const flaggedAndIrrelevant = fieldDisplay({
    hostContacted: false, weContacted: true, flagForAnalysis: true, deemedIrrelevant: true, comments: '',
  })
  expect(flaggedAndIrrelevant.props.children[0].props.content).toBe('We Contacted Host')
  expect(flaggedAndIrrelevant.props.children[1].props.content).toBe('Flag for Analysis')
  expect(flaggedAndIrrelevant.props.children[2].props.content).toBe('Deemed Irrelevant')

  store.clearActions()
  const { searchMme, onSubmit } = wrapper.findWhere(
    n => n.props().searchMme && n.props().onSubmit,
  ).first().props()
  searchMme()
  expect(store.getActions().some(({ type }) => type === 'REQUEST_MME_MATCHES')).toBe(true)
  expect(() => onSubmit({ comments: 'updated' })).not.toThrow()
})

test('renders an individual whose submission and data are missing optional fields', () => {
  const { I021475_na19675_1: individual, ...restIndividuals } = STATE_WITH_2_FAMILIES.individualsByGuid
  const { features, ...individualWithoutFeatures } = individual
  const submissionWithoutGenotypes = {
    ...STATE_WITH_2_FAMILIES.mmeSubmissionsByGuid.MS021475_na19675_1, geneVariants: [], phenotypes: [],
  }
  const { MR0005038_HK018_0047: result1, ...restResults } = STATE_WITH_2_FAMILIES.mmeResultsByGuid
  const { institution, ...contactWithoutInstitution } = result1.patient.contact
  const resultWithoutInstitution = {
    ...result1, patient: { ...result1.patient, contact: contactWithoutInstitution },
  }

  const store = configureStore({
    ...STATE_WITH_2_FAMILIES,
    individualsByGuid: { ...restIndividuals, I021475_na19675_1: individualWithoutFeatures },
    mmeSubmissionsByGuid: {
      ...STATE_WITH_2_FAMILIES.mmeSubmissionsByGuid,
      MS021475_na19675_1: submissionWithoutGenotypes,
    },
    mmeResultsByGuid: { ...restResults, MR0005038_HK018_0047: resultWithoutInstitution },
    savedVariantFamilies: { F011652_1: { loaded: true } },
    modal: { 'I021475_na19675_1_-_UpdateMmeSubmission': { open: true } },
  })

  const wrapper = mount(
    <Provider store={store}>
      <Matchmaker match={MATCH_CREATE_SUBMISSION} />
    </Provider>,
  )

  // no submitted genotypes/phenotypes renders "None" instead of the tables
  const wrapperText = wrapper.text()
  expect(wrapperText).toContain('None')

  // individual with no features falls back to an empty phenotypes list in the edit form
  const phenotypesTable = wrapper.find({ idField: 'id' })
  expect(phenotypesTable.first().prop('data')).toEqual([])

  // contact with no institution renders without crashing and does not show the removed institution
  expect(wrapperText).toContain('James Crowley')
  expect(wrapperText).not.toContain('UNC Chapel Hill')
})

test('renders an error page when no individuals are found for the family', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  const wrapper = mount(
    <Provider store={store}>
      <Matchmaker match={MATCH_UNKNOWN_FAMILY} />
    </Provider>,
  )

  expect(wrapper.find('MatchmakerIndividual').exists()).toBe(false)
  expect(wrapper.text()).toContain('Error 404')
})

test('fetches mme matches on mount when the submission has no recorded gene variants', () => {
  const { geneVariants, ...submissionWithoutGeneVariants } = STATE_WITH_2_FAMILIES.mmeSubmissionsByGuid.MS021475_na19675_1
  const store = configureStore({
    ...STATE_WITH_2_FAMILIES,
    mmeSubmissionsByGuid: {
      ...STATE_WITH_2_FAMILIES.mmeSubmissionsByGuid,
      MS021475_na19675_1: submissionWithoutGeneVariants,
    },
  })

  mount(
    <Provider store={store}>
      <Matchmaker match={MATCH_CREATE_SUBMISSION} />
    </Provider>,
  )

  expect(HttpRequestHelper).toHaveBeenCalledWith(
    '/api/matchmaker/get_mme_matches/MS021475_na19675_1', expect.any(Function), expect.any(Function),
  )
})

test('does not re-fetch mme matches on mount when gene variants are already recorded', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  mount(
    <Provider store={store}>
      <Matchmaker match={MATCH_CREATE_SUBMISSION} />
    </Provider>,
  )

  expect(HttpRequestHelper).not.toHaveBeenCalledWith(
    '/api/matchmaker/get_mme_matches/MS021475_na19675_1', expect.any(Function), expect.any(Function),
  )
})

test('submits an mme submission status update', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <Matchmaker match={MATCH_CREATE_SUBMISSION} />
    </Provider>,
  )

  const onSubmit = wrapper.find({ field: 'matchStatus' }).first().prop('onSubmit')
  onSubmit({ comments: 'Looks promising', matchmakerResultGuid: 'MR0005038_HK018_0047' })

  expect(HttpRequestHelper).toHaveBeenCalledWith(
    '/api/matchmaker/result_status/MR0005038_HK018_0047/update', expect.any(Function),
  )
})

test('submits an mme contact notes update', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <Matchmaker match={MATCH_CREATE_SUBMISSION} />
    </Provider>,
  )

  const onSubmit = wrapper.find({ idField: 'contactInstitution' }).first().prop('onSubmit')
  onSubmit({ institution: 'UNC Chapel Hill', comments: 'Reached out via email' })

  expect(HttpRequestHelper).toHaveBeenCalledWith(
    '/api/matchmaker/contact_notes/UNC Chapel Hill/update', expect.any(Function),
  )
})

test('sends an mme contact email', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <Matchmaker match={MATCH_CREATE_SUBMISSION} />
    </Provider>,
  )

  const onSubmit = wrapper.find({ matchmakerResultGuid: 'MR0005038_HK018_0047' }).filterWhere(
    n => typeof n.prop('onSubmit') === 'function',
  ).first().prop('onSubmit')
  onSubmit({ matchmakerResultGuid: 'MR0005038_HK018_0047', body: 'Hello' })

  expect(HttpRequestHelper).toHaveBeenCalledWith(
    '/api/matchmaker/send_email/MR0005038_HK018_0047', expect.any(Function),
  )
})

test('searches for new mme matches and finalizes the search', async () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <Matchmaker match={MATCH_CREATE_SUBMISSION} />
    </Provider>,
  )

  const { searchMme } = wrapper.findWhere(
    n => n.props().searchMme && n.props().onSubmit,
  ).first().props()

  HttpRequestHelper.mockClear()
  searchMme()

  expect(HttpRequestHelper).toHaveBeenCalledWith(
    '/api/matchmaker/get_mme_nodes', expect.any(Function), expect.any(Function),
  )
  const [, onGetNodesSuccess] = HttpRequestHelper.mock.calls.find(([url]) => url === '/api/matchmaker/get_mme_nodes')
  onGetNodesSuccess({ mmeNodes: [] })

  // flush the chained promises triggered by the get_mme_nodes success callback
  await Promise.resolve().then().then().then()

  expect(HttpRequestHelper).toHaveBeenCalledWith(
    '/api/matchmaker/search_local_mme_matches/MS021475_na19675_1', expect.any(Function), expect.any(Function),
  )
  const [, onLocalMatchesSuccess] = HttpRequestHelper.mock.calls.find(
    ([url]) => url === '/api/matchmaker/search_local_mme_matches/MS021475_na19675_1',
  )
  onLocalMatchesSuccess({ incomingQueryGuid: 'q1' })

  await Promise.resolve().then().then().then()

  expect(HttpRequestHelper).toHaveBeenCalledWith(
    '/api/matchmaker/finalize_mme_search/MS021475_na19675_1', expect.any(Function), expect.any(Function),
  )
})

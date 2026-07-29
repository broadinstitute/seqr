import React from 'react'
import { mount, shallow, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import cloneDeep from 'lodash/cloneDeep'
import { mockFetchResponse, mockFetchRejection, flushAll, getLastFetchUrl } from 'shared/utils/testHelpers'
import { STATE_WITH_2_FAMILIES } from '../fixtures'
import Matchmaker from './Matchmaker'

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

const fetchedUrl = urlPrefix => fetch.mock.calls.some(([url]) => url.startsWith(urlPrefix))

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

test('renders the affected individual with a matchmaker submission', async () => {
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

  // searchMme's own get_mme_nodes request has an onError handler, so a rejection is handled
  // internally (dispatches an error action) without any further chained requests
  mockFetchRejection(new Error('ignored'))
  searchMme()
  expect(store.getActions().some(({ type }) => type === 'REQUEST_MME_MATCHES')).toBe(true)

  // updateMmeSubmission's HttpRequestHelper has no onError, so a rejection propagates out as a
  // rejected promise instead of triggering its onSuccess (which would otherwise cascade into a
  // second searchMmeMatches call) - catch it explicitly so it isn't left unhandled
  mockFetchRejection(new Error('ignored'))
  let submitResult
  expect(() => { submitResult = onSubmit({ comments: 'updated' }) }).not.toThrow()
  await submitResult.catch(() => {})
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
    modal: {'I021475_na19675_1_-_UpdateMmeSubmission': {open: true } },
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

  expect(fetchedUrl('/api/matchmaker/get_mme_matches/MS021475_na19675_1')).toBe(true)
})

test('does not re-fetch mme matches on mount when gene variants are already recorded', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  mount(
    <Provider store={store}>
      <Matchmaker match={MATCH_CREATE_SUBMISSION} />
    </Provider>,
  )

  expect(fetchedUrl('/api/matchmaker/get_mme_matches/MS021475_na19675_1')).toBe(false)
})

test('dispatches an error action when fetching mme matches on mount fails', async () => {
  const {
    geneVariants, ...submissionWithoutGeneVariants
  } = STATE_WITH_2_FAMILIES.mmeSubmissionsByGuid.MS021475_na19675_1
  const store = configureStore({
    ...STATE_WITH_2_FAMILIES,
    mmeSubmissionsByGuid: {
      ...STATE_WITH_2_FAMILIES.mmeSubmissionsByGuid,
      MS021475_na19675_1: submissionWithoutGeneVariants,
    },
  })

  mockFetchRejection(new Error('mme matches request failed'))

  mount(
    <Provider store={store}>
      <Matchmaker match={MATCH_CREATE_SUBMISSION} />
    </Provider>,
  )
  await flushAll()

  expect(store.getActions()).toContainEqual(
    expect.objectContaining({ type: 'RECEIVE_MME_MATCHES', error: 'mme matches request failed' }),
  )
})

test('submits an mme submission status update', async () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <Matchmaker match={MATCH_CREATE_SUBMISSION} />
    </Provider>,
  )

  const onSubmit = wrapper.find({ field: 'matchStatus' }).first().prop('onSubmit')
  onSubmit({ comments: 'Looks promising', matchmakerResultGuid: 'MR0005038_HK018_0047' })
  await flushAll()

  expect(getLastFetchUrl()).toEqual('/api/matchmaker/result_status/MR0005038_HK018_0047/update')
})

test('submits an mme contact notes update', async () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <Matchmaker match={MATCH_CREATE_SUBMISSION} />
    </Provider>,
  )

  const onSubmit = wrapper.find({ idField: 'contactInstitution' }).first().prop('onSubmit')
  onSubmit({ institution: 'UNC Chapel Hill', comments: 'Reached out via email' })
  await flushAll()

  expect(getLastFetchUrl()).toEqual('/api/matchmaker/contact_notes/UNC Chapel Hill/update')
})

test('sends an mme contact email', async () => {
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
  await flushAll()

  expect(getLastFetchUrl()).toEqual('/api/matchmaker/send_email/MR0005038_HK018_0047')
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

  // queue responses in the exact order fetch() will be called across the chained requests
  mockFetchResponse({ mmeNodes: [] })
  mockFetchResponse({ incomingQueryGuid: 'q1' })

  searchMme()
  await flushAll(12)

  expect(fetchedUrl('/api/matchmaker/get_mme_nodes')).toBe(true)
  expect(fetchedUrl('/api/matchmaker/search_local_mme_matches/MS021475_na19675_1')).toBe(true)
  expect(getLastFetchUrl()).toEqual('/api/matchmaker/finalize_mme_search/MS021475_na19675_1?incomingQueryGuid=q1')
})

test('collects errors from each stage of an mme search and reports them when finalizing fails', async () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <Matchmaker match={MATCH_CREATE_SUBMISSION} />
    </Provider>,
  )

  const { searchMme } = wrapper.findWhere(
    n => n.props().searchMme && n.props().onSubmit,
  ).first().props()

  // queue responses/rejections in the exact order fetch() will be called across the chained
  // requests: get_mme_nodes, the local match search, one search per remote node (one succeeds,
  // one fails), and finally the finalize request itself failing
  mockFetchResponse({ mmeNodes: ['node_ok', 'node_fail'] })
  mockFetchRejection(new Error('local match search failed'))
  mockFetchResponse({})
  mockFetchRejection(new Error('node_fail search failed'))
  mockFetchRejection(new Error('finalize request failed'))

  searchMme()
  await flushAll(12)

  expect(fetchedUrl('/api/matchmaker/search_mme_matches/MS021475_na19675_1/node_ok')).toBe(true)
  expect(fetchedUrl('/api/matchmaker/search_mme_matches/MS021475_na19675_1/node_fail')).toBe(true)
  expect(store.getActions()).toContainEqual(
    expect.objectContaining({ type: 'RECEIVE_MME_MATCHES', error: 'finalize request failed' }),
  )
})

test('deletes an mme submission without cascading into a new search', async () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <Matchmaker match={MATCH_CREATE_SUBMISSION} />
    </Provider>,
  )

  mockFetchResponse({ mmeSubmissionsByGuid: { MS021475_na19675_1: { deletedDate: '2020-01-01' } } })
  wrapper.find('DispatchRequestButton').filterWhere(n => n.prop('buttonContent') === 'Delete Submission')
    .first().prop('onSubmit')()
  await flushAll()

  expect(fetchedUrl('/api/matchmaker/get_mme_nodes')).toBe(false)
})

test('cascades into a new mme search after successfully updating a submission', async () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <Matchmaker match={MATCH_CREATE_SUBMISSION} />
    </Provider>,
  )

  const { onSubmit } = wrapper.findWhere(
    n => n.props().searchMme && n.props().onSubmit,
  ).first().props()

  // queue responses for the update itself, then the searchMmeMatches cascade it triggers on success
  mockFetchResponse({ mmeSubmissionsByGuid: { MS021475_na19675_1: {} } })
  mockFetchResponse({ mmeNodes: [] })
  mockFetchResponse({ incomingQueryGuid: 'q2' })

  await onSubmit({ comments: 'updated' })
  await flushAll(12)

  expect(fetchedUrl('/api/matchmaker/get_mme_nodes')).toBe(true)
  expect(getLastFetchUrl()).toEqual('/api/matchmaker/finalize_mme_search/MS021475_na19675_1?incomingQueryGuid=q2')
})

test('renders an individual with no tagged variants', () => {
  const store = configureStore({
    ...STATE_WITH_2_FAMILIES,
    savedVariantsByGuid: {},
    savedVariantFamilies: { F011652_2: { loaded: true } },
    modal: { 'I021475_na19675_2_-_CreateMmeSubmission': { open: true } },
  })

  const wrapper = mount(
    <Provider store={store}>
      <Matchmaker match={MATCH} />
    </Provider>,
  )

  const genotypesTable = wrapper.find({ familyGuid: 'F011652_2' })
  expect(genotypesTable.first().prop('data')).toEqual([])
})

test('renders an individual with no variant genotypes', () => {
  const noGenotypesState = cloneDeep(STATE_WITH_2_FAMILIES)
  noGenotypesState.savedVariantsByGuid.SV0000004_116042722_r0390_1000.genotypes = undefined
  noGenotypesState.savedVariantFamilies = { F011652_1: { loaded: true } }
  noGenotypesState.modal = {'I021475_na19675_1_-_UpdateMmeSubmission': {open: true } }

  const wrapper = mount(
    <Provider store={configureStore(noGenotypesState)}>
      <Matchmaker match={MATCH_CREATE_SUBMISSION} />
    </Provider>,
  )

  const genotypesData = wrapper.find({ familyGuid: 'F011652_1' }).first().prop('data')
  expect(genotypesData).toEqual([
    expect.objectContaining({ variantId: 'SV0000002_1248367227_r0390_100-ENSG00000228198', numAlt: 2 }),
    expect.objectContaining({ variantId: 'SV0000004_116042722_r0390_1000-ENSG00000228198' }),
  ])
  expect('numAlt' in genotypesData[1]).toBe(false)
})

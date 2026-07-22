import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'
import { CASE_REVIEW_TABLE_NAME } from '../../constants'

import IndividualRow, { IndividualRowComponent } from './IndividualRow'
import { STATE_WITH_2_FAMILIES } from '../../fixtures'

jest.mock('../../reducers', () => ({
  ...jest.requireActual('../../reducers'),
  updateIndividuals: values => ({ type: 'UPDATE_INDIVIDUALS', ...values }),
  updateIndividualIGV: values => ({ type: 'UPDATE_INDIVIDUAL_IGV', ...values }),
}))

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

const TEST_INDIVIDUAL_GUID = 'I021475_na19675_1'

test('toggles compact/full individual details via CollapsableLayout when deeply rendered', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <IndividualRow
          family={STATE_WITH_2_FAMILIES.familiesByGuid.F011652_1}
          individual={STATE_WITH_2_FAMILIES.individualsByGuid.I021475_na19675_1}
          tableName={CASE_REVIEW_TABLE_NAME}
        />
      </MemoryRouter>
    </Provider>,
  )

  // the pedigree/IGV edit buttons are always rendered, regardless of collapsed state
  const baseFieldCount = wrapper.find('BaseFieldView').length

  const toggle = wrapper.find('CollapsableLayout').find('Icon[name="dropdown"]')
  expect(toggle.exists()).toBe(true)

  toggle.first().simulate('click')
  wrapper.update()

  // after toggling, the full set of case review detail fields is rendered in addition
  expect(wrapper.find('BaseFieldView').length).toBeGreaterThan(baseFieldCount)
})

test('renders individual data details, submitted MME status, and age details for the non-case-review table', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <IndividualRow
          family={STATE_WITH_2_FAMILIES.familiesByGuid.F011652_1}
          individual={STATE_WITH_2_FAMILIES.individualsByGuid.I021475_na19675_1}
        />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.text()).toContain('Submitted to MME')
  expect(wrapper.text()).toContain('Age:Deceased at age 10 - Born in 2010')
  expect(wrapper.text()).toContain('Age of Onset:Adult onset')
  expect(wrapper.text()).toContain('Expected Mode of Inheritance:Sporadic, X-linked recessive inheritance')
  expect(wrapper.text()).toContain('Assisted Reproduction:Intrauterine insemination')
  expect(wrapper.text()).toContain('Maternal Ancestry:White / Asian')
  expect(wrapper.text()).toContain('Imputed Population :African')
  expect(wrapper.text()).toContain('Pre-discovery OMIM disorders:10243')
  expect(wrapper.text()).toContain('Previously Tested Genes:LGMD panel  (15 genes, lab A, 2013, NGS, negative)')
})

test('renders individual data details, removed MME status, and age details', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <IndividualRow
          family={STATE_WITH_2_FAMILIES.familiesByGuid.F011652_1}
          individual={STATE_WITH_2_FAMILIES.individualsByGuid.I021476_na19678_1}
        />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.text()).toContain('Removed from MME: 1/1/2020')
  expect(wrapper.text()).toContain('Show Phenotype Prioritized Genes')
  expect(wrapper.text()).toContain('RNAseq Results')
  expect(wrapper.text()).toContain(`Age:${new Date().getFullYear() - 1980}`)
})

test('dispatches pedigree and IGV updates and renders parent/IGV select and gene fields when editing', () => {
  const pedigreeModalId = `edit_-_${TEST_INDIVIDUAL_GUID}_-_coreEdit_-_undefined`
  const igvModalId = `edit_-_${TEST_INDIVIDUAL_GUID}_-_ IGVEdit_-_undefined`
  const rejectedGenesModalId = `edit_-_${TEST_INDIVIDUAL_GUID}_-_rejectedGenes_-_undefined`
  const arModalId = `edit_-_${TEST_INDIVIDUAL_GUID}_-_ar_-_undefined`
  const ageModalId = `edit_-_${TEST_INDIVIDUAL_GUID}_-_age_-_undefined`

  const store = configureStore({
    ...STATE_WITH_2_FAMILIES,
    modal: {
      [pedigreeModalId]: { open: true },
      [igvModalId]: { open: true },
      [rejectedGenesModalId]: { open: true },
      [arModalId]: { open: true },
      [ageModalId]: { open: true },
    },
  })

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <IndividualRow
          family={STATE_WITH_2_FAMILIES.familiesByGuid.F011652_1}
          individual={STATE_WITH_2_FAMILIES.individualsByGuid.I021475_na19675_1}
        />
      </MemoryRouter>
    </Provider>,
  )

  // mapParentOptionsStateToProps and mapIgvOptionsStateToProps are exercised by rendering these connected fields
  expect(wrapper.find('Connect(Select)').length).toBeGreaterThan(0)
  expect(wrapper.find('Connect(LoadOptionsSelect)').length).toBe(1)

  // GeneEntry fields for the rejectedGenes list
  expect(wrapper.find('ForwardRef(Field)[name="rejectedGenes[0].gene"]').length).toBe(1)

  // ButtonRadioGroup groupContainer for the 'ar' subfields
  expect(wrapper.find('Inputs__RadioButtonGroup').length).toBeGreaterThan(0)

  const filePathField = wrapper.find('ForwardRef(Field)[name="filePath"]')
  expect(filePathField.prop('formatOption')('gs://test.cram')).toBe('gs://test.cram')

  const deathYearField = wrapper.find('ForwardRef(Field)[name="deathYear"]')
  expect(deathYearField.prop('format')(0)).toBe(0)
  expect(deathYearField.prop('format')(undefined)).toBe(-1)
  expect(deathYearField.prop('parse')(-1)).toBe(null)
  expect(deathYearField.prop('parse')(2020)).toBe(2020)

  const pedigreeEdit = wrapper.find('Connect(FormWrapper)').filterWhere(n => n.prop('modalName') === pedigreeModalId)
  pedigreeEdit.first().prop('onSubmit')({ individualGuid: TEST_INDIVIDUAL_GUID, sex: 'M' })

  const igvEdit = wrapper.find('Connect(FormWrapper)').filterWhere(n => n.prop('modalName') === igvModalId)
  igvEdit.first().prop('onSubmit')({ filePath: 'gs://test.cram' })

  const actions = store.getActions()
  const pedigreeAction = actions.find(action => action.type === 'UPDATE_INDIVIDUALS')
  const igvAction = actions.find(action => action.type === 'UPDATE_INDIVIDUAL_IGV')

  expect(pedigreeAction.individuals).toEqual([{ individualGuid: TEST_INDIVIDUAL_GUID, sex: 'M' }])
  expect(igvAction.filePath).toBe('gs://test.cram')
})

const PROJECT = STATE_WITH_2_FAMILIES.projectsByGuid.R0237_1000_genomes_demo

const renderIndividualRowComponent = (individual, props = {}) => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  return mount(
    <Provider store={store}>
      <MemoryRouter>
        <IndividualRowComponent project={PROJECT} individual={individual} {...props} />
      </MemoryRouter>
    </Provider>,
  )
}

test('renders case review status without a last modified date or user', () => {
  const wrapper = renderIndividualRowComponent(
    {
      ...STATE_WITH_2_FAMILIES.individualsByGuid.I021475_na19675_1,
      caseReviewStatusLastModifiedDate: null,
      caseReviewStatusLastModifiedBy: null,
    },
    { tableName: CASE_REVIEW_TABLE_NAME },
  )

  expect(wrapper.text()).not.toContain('CHANGED ON')
})

test('renders case review status with a last modified date and user', () => {
  const wrapper = renderIndividualRowComponent(
    {
      ...STATE_WITH_2_FAMILIES.individualsByGuid.I021475_na19675_1,
      caseReviewStatusLastModifiedDate: '2016-12-05T10:29:00.000Z',
      caseReviewStatusLastModifiedBy: 'test user',
    },
    { tableName: CASE_REVIEW_TABLE_NAME },
  )

  expect(wrapper.text()).toContain('CHANGED ON')
  expect(wrapper.text()).toContain('BY test user')
})

test('renders RNAseq results link when only splice outlier data type is present', () => {
  const wrapper = renderIndividualRowComponent({
    ...STATE_WITH_2_FAMILIES.individualsByGuid.I021476_na19678_1,
    rnaSample: { loadedDate: '2020-01-01T12:00:00.000Z', dataTypes: ['S'] },
  })

  expect(wrapper.text()).toContain('RNAseq Results')
})

test('does not render RNAseq results link when no outlier data types are present', () => {
  const wrapper = renderIndividualRowComponent({
    ...STATE_WITH_2_FAMILIES.individualsByGuid.I021476_na19678_1,
    rnaSample: { loadedDate: '2020-01-01T12:00:00.000Z', dataTypes: ['T'] },
  })

  expect(wrapper.text()).not.toContain('RNAseq Results')
})

test('renders a rejected gene without comments', () => {
  const wrapper = renderIndividualRowComponent({
    ...STATE_WITH_2_FAMILIES.individualsByGuid.I021475_na19675_1,
    rejectedGenes: [{ gene: 'BRCA1' }],
  })

  expect(wrapper.text()).toContain('Previously Tested Genes:BRCA1')
})

test('renders age details when death year is 0 and birth year is unknown', () => {
  const wrapper = renderIndividualRowComponent({
    ...STATE_WITH_2_FAMILIES.individualsByGuid.I021475_na19675_1,
    birthYear: null,
    deathYear: 0,
  })

  expect(wrapper.text()).toContain('Age:Deceased (date unknown)')
})

test('renders age details when death year is known but birth year is unknown', () => {
  const wrapper = renderIndividualRowComponent({
    ...STATE_WITH_2_FAMILIES.individualsByGuid.I021475_na19675_1,
    birthYear: null,
    deathYear: 2015,
  })

  expect(wrapper.text()).toContain('Age:Deceased in 2015')
})

test('renders unknown age when neither birth year nor death year is known', () => {
  const wrapper = renderIndividualRowComponent({
    ...STATE_WITH_2_FAMILIES.individualsByGuid.I021475_na19675_1,
    birthYear: null,
    deathYear: null,
  })

  expect(wrapper.text()).toContain('Age:Unknown')
})

test('renders an unmapped population code as-is', () => {
  const wrapper = renderIndividualRowComponent({
    ...STATE_WITH_2_FAMILIES.individualsByGuid.I021475_na19675_1,
    population: 'XYZ',
  })

  expect(wrapper.text()).toMatch(/Imputed Population\s*:XYZ/)
})

test('renders "Not Loaded" when no population is set', () => {
  const wrapper = renderIndividualRowComponent(
    {
      ...STATE_WITH_2_FAMILIES.individualsByGuid.I021475_na19675_1,
      population: null,
    },
    { project: { ...PROJECT, isAnalystProject: true } },
  )

  expect(wrapper.text()).toMatch(/Imputed Population\s*:Not Loaded/)
})

test('only shows active or first/last inactive samples from an explicit datasets list', () => {
  const wrapper = renderIndividualRowComponent(
    STATE_WITH_2_FAMILIES.individualsByGuid.I021475_na19675_1,
    {
      datasets: [
        { loadedDate: '2020-01-01', sampleType: 'WES', datasetType: 'SNV_INDEL', isActive: false },
        { loadedDate: '2020-01-02', sampleType: 'WES', datasetType: 'SNV_INDEL', isActive: true },
        { loadedDate: '2020-01-03', sampleType: 'WES', datasetType: 'SNV_INDEL', isActive: false },
        { loadedDate: '2020-01-04', sampleType: 'WES', datasetType: 'SNV_INDEL', isActive: false },
      ],
    },
  )

  // reversed order: 01-04 (i=0, inactive, kept as first), 01-03 (i=1, inactive, dropped),
  // 01-02 (i=2, active, kept), 01-01 (i=3, inactive, kept as last)
  const samples = wrapper.find('Memo()').filterWhere(n => n.prop('sampleType') === 'WES')
  expect(samples).toHaveLength(3)
  expect(samples.map(n => n.prop('loadedDate'))).toEqual(['2020-01-04', '2020-01-02', '2020-01-01'])
})

test('renders parent options select as disabled when there are no eligible parents', () => {
  const parentPedigreeModalId = 'edit_-_I021476_na19678_2_-_coreEdit_-_undefined'
  const store = configureStore({
    ...STATE_WITH_2_FAMILIES,
    modal: { [parentPedigreeModalId]: { open: true } },
  })

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <IndividualRow
          family={STATE_WITH_2_FAMILIES.familiesByGuid.F011652_2}
          individual={STATE_WITH_2_FAMILIES.individualsByGuid.I021476_na19678_2}
          tableName={CASE_REVIEW_TABLE_NAME}
        />
      </MemoryRouter>
    </Provider>,
  )

  const motherSelect = wrapper.find('Select').filterWhere(n => n.prop('name') === 'maternalGuid')
  expect(motherSelect.first().prop('disabled')).toBe(true)
  expect(motherSelect.first().prop('options')).toEqual([])
})

test('renders disorders and candidate genes item inputs when editing', () => {
  const disordersModalId = `edit_-_${TEST_INDIVIDUAL_GUID}_-_disorders_-_undefined`
  const candidateGenesModalId = `edit_-_${TEST_INDIVIDUAL_GUID}_-_candidateGenes_-_undefined`

  const store = configureStore({
    ...STATE_WITH_2_FAMILIES,
    modal: {
      [disordersModalId]: { open: true },
      [candidateGenesModalId]: { open: true },
    },
  })

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <IndividualRow
          family={STATE_WITH_2_FAMILIES.familiesByGuid.F011652_1}
          individual={STATE_WITH_2_FAMILIES.individualsByGuid.I021475_na19675_1}
        />
      </MemoryRouter>
    </Provider>,
  )

  // disorders list item is edited via a plain input (no react-final-form `input` prop forwarded)
  expect(wrapper.find('input[value=10243]').exists()).toBe(true)

  // candidateGenes has no existing values, so a blank searchable gene input is rendered
  expect(wrapper.find('ForwardRef(Field)[name="candidateGenes[0].gene"]').length).toBe(1)
})

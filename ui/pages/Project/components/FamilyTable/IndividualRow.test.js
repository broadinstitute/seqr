import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'
import { flushAll, getLastFetchUrl, getLastFetchBody } from 'shared/utils/testHelpers'
import { CASE_REVIEW_TABLE_NAME } from '../../constants'

import IndividualRow from './IndividualRow'
import { STATE_WITH_2_FAMILIES } from '../../fixtures'

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
  expect(wrapper.text()).toContain('CHANGED ON')
  expect(wrapper.text()).toContain('BY test user')

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
  expect(wrapper.text()).toContain('Previously Tested Genes:BRCA1 LGMD panel  (15 genes, lab A, 2013, NGS, negative)')

  expect(wrapper.text()).not.toContain('RNAseq Results')
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

  expect(wrapper.text()).not.toContain('Imputed Population')
})

test('dispatches pedigree and IGV updates and renders parent/IGV select and gene fields when editing', async () => {
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
  await flushAll()

  expect(getLastFetchUrl()).toEqual('/api/project/R0237_1000_genomes_demo/edit_individuals')
  expect(getLastFetchBody()).toEqual(
    expect.objectContaining({ individuals: [{ individualGuid: TEST_INDIVIDUAL_GUID, sex: 'M' }] }),
  )

  const igvEdit = wrapper.find('Connect(FormWrapper)').filterWhere(n => n.prop('modalName') === igvModalId)
  igvEdit.first().prop('onSubmit')({ individualGuid: TEST_INDIVIDUAL_GUID, filePath: 'gs://test.cram' })
  await flushAll()

  expect(getLastFetchUrl()).toEqual('/api/individual/I021475_na19675_1/update_igv_sample')
  expect(getLastFetchBody()).toEqual({ individualGuid: TEST_INDIVIDUAL_GUID, filePath: 'gs://test.cram' })

  // deleting an individual (the pedigree edit form's delete confirm) posts to the delete action
  pedigreeEdit.first().prop('onSubmit')({ individualGuid: TEST_INDIVIDUAL_GUID, delete: true })
  await flushAll()

  expect(getLastFetchUrl()).toEqual('/api/project/R0237_1000_genomes_demo/delete_individuals')
  expect(getLastFetchBody()).toEqual(
    expect.objectContaining({ individuals: [{ individualGuid: TEST_INDIVIDUAL_GUID, delete: true }], delete: true }),
  )
})

test('renders case review status without a last modified date or user', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <IndividualRow
          family={STATE_WITH_2_FAMILIES.familiesByGuid.F011652_2}
          individual={STATE_WITH_2_FAMILIES.individualsByGuid.I021474_na19679_2}
          tableName={CASE_REVIEW_TABLE_NAME}
        />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.text()).not.toContain('CHANGED ON')
})

test('renders RNAseq results link when only splice outlier data type is present', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <IndividualRow
          family={STATE_WITH_2_FAMILIES.familiesByGuid.F011652_1}
          individual={STATE_WITH_2_FAMILIES.individualsByGuid.I021474_na19679_1}
        />
      </MemoryRouter>
    </Provider>,
  )
  expect(wrapper.text()).toContain('RNAseq Results')
  expect(wrapper.text()).toContain('Age:Deceased (date unknown)')
  expect(wrapper.text()).toMatch(/Imputed Population\s*:XYZ/)
})

test('renders age details when death year is known but birth year is unknown', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <IndividualRow
          family={STATE_WITH_2_FAMILIES.familiesByGuid.F011652_2}
          individual={STATE_WITH_2_FAMILIES.individualsByGuid.I021476_na19678_2}
        />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.text()).toContain('Age:Deceased in 2015')
})

test('renders unknown age when neither birth year nor death year is known', () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <IndividualRow
          family={STATE_WITH_2_FAMILIES.familiesByGuid.F011652_2}
          individual={STATE_WITH_2_FAMILIES.individualsByGuid.I021475_na19675_2}
        />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.text()).toContain('Age:Unknown')
  expect(wrapper.text()).not.toContain('Imputed Population')
})

test('renders "Not Loaded" when no population is set', () => {
  const store = configureStore({
    ...STATE_WITH_2_FAMILIES,
    projectsByGuid: {
      ...STATE_WITH_2_FAMILIES.projectsByGuid,
      R0237_1000_genomes_demo: {
        ...STATE_WITH_2_FAMILIES.projectsByGuid.R0237_1000_genomes_demo,
        isAnalystProject: true,
      },
    },
  })

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <IndividualRow
          individual={STATE_WITH_2_FAMILIES.individualsByGuid.I021475_na19675_2}
        />
      </MemoryRouter>
    </Provider>,
  )

  expect(wrapper.text()).toMatch(/Imputed Population\s*:Not Loaded/)
})

test('only shows active or first/last inactive samples from an explicit datasets list', () => {
  const individualGuid = 'I021475_na19675_1'
  const loadedDates = ['2020-01-01', '2020-01-02', '2020-01-03', '2020-01-04']
  const datasetsByGuid = loadedDates.reduce((acc, loadedDate, i) => ({
    ...acc,
    [`D_${loadedDate}`]: {
      datasetGuid: `D_${loadedDate}`,
      datasetType: 'SNV_INDEL',
      sampleType: 'WES',
      loadedDate,
      activeIndividuals: i === 1 ? [individualGuid] : [],
      inactiveIndividuals: i === 1 ? [] : [individualGuid],
    },
  }), {})

  const store = configureStore({
    ...STATE_WITH_2_FAMILIES,
    datasetsByGuid: { ...STATE_WITH_2_FAMILIES.datasetsByGuid, ...datasetsByGuid },
  })

  const wrapper = mount(
    <Provider store={store}>
      <MemoryRouter>
        <IndividualRow
          individual={STATE_WITH_2_FAMILIES.individualsByGuid.I021475_na19675_1}
        />
      </MemoryRouter>
    </Provider>,
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

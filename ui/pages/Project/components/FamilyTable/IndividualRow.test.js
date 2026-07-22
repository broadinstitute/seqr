import React from 'react'
import { shallow, mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'
import { MemoryRouter } from 'react-router-dom'
import { CASE_REVIEW_TABLE_NAME } from '../../constants'

import IndividualRow from './IndividualRow'
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

  expect(wrapper.text()).toContain('Removed from MME: 12/31/2019')
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

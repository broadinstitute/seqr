import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureMockStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'

import { mockFetchResponse, getLastFetchUrl, getLastFetchBody } from 'shared/utils/testHelpers'
import CreateVariantButtons from './CreateVariantButton'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

const configureStore = configureMockStore([thunk])

const FAMILY = STATE_WITH_2_FAMILIES.familiesByGuid.F011652_1

test('renders manual variant and SV buttons when the project is editable', async () => {
  const store = configureStore(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <CreateVariantButtons family={FAMILY} />
    </Provider>
  )

  expect(wrapper.text()).toContain('Add Manual Variant')
  expect(wrapper.text()).toContain('Add Manual SV')

  const { onSubmit } = wrapper.findWhere(n => n.props().onSubmit && n.props().family).first().props()

  mockFetchResponse({ savedVariantsByGuid: { SV001: {} } })
  const dispatchCountBeforeSuccess = store.getActions().length
  await onSubmit({ chrom: '1' })

  expect(getLastFetchUrl()).toEqual(`/api/saved_variant/create_manual/${FAMILY.familyGuid}`)
  expect(getLastFetchBody()).toEqual({ chrom: '1' })

  expect(store.getActions().length).toBe(dispatchCountBeforeSuccess + 1)
  expect(store.getActions()[dispatchCountBeforeSuccess]).toEqual(
    { type: 'RECEIVE_DATA', updatesById: { savedVariantsByGuid: { SV001: {} } } },
  )
})

test('opens the manual SNV modal and exercises the form field callbacks', () => {
  const store = configureStore({
    ...STATE_WITH_2_FAMILIES,
    savedVariantFamilies: { F011652_1: { loaded: true } },
    modal: { 'F011652_1-addVariant-Variant': { open: true } },
  })
  const wrapper = mount(
    <Provider store={store}>
      <CreateVariantButtons family={FAMILY} />
    </Provider>,
  )

  const hgvscField = wrapper.find('ForwardRef(Field)[name="hgvsc"]')
  expect(hgvscField.exists()).toBe(true)
  const validateHasTranscriptId = hgvscField.first().prop('validate')
  expect(validateHasTranscriptId(undefined, {})).toBeUndefined()
  expect(validateHasTranscriptId('ENST1.1:c.1A>T', {}, {}, 'hgvsc')).toBe(
    'Transcript ID is required to include hgvsc',
  )
  expect(validateHasTranscriptId('ENST1.1:c.1A>T', { mainTranscriptId: 'ENST1' })).toBeUndefined()

  const zygosityFields = wrapper.find('ForwardRef(Field)[name^="genotypes."]')
  expect(zygosityFields.length).toBeGreaterThan(0)
  const zygosityField = zygosityFields.first()
  expect(zygosityField.prop('parse')(2)).toEqual({ numAlt: 2 })
  expect(zygosityField.prop('format')({ numAlt: 2 })).toBe(2)
  expect(zygosityField.prop('format')(undefined)).toBeUndefined()
})

test('exercises the tags form field format/parse/validate callbacks', () => {
  const store = configureStore({
    ...STATE_WITH_2_FAMILIES,
    savedVariantFamilies: { F011652_1: { loaded: true } },
    modal: { 'F011652_1-addVariant-Variant': { open: true } },
  })
  const wrapper = mount(
    <Provider store={store}>
      <CreateVariantButtons family={FAMILY} />
    </Provider>,
  )

  const tagsField = wrapper.find('ForwardRef(Field)[name="tags"]').first()

  expect(tagsField.prop('format')([{ name: 'Review' }])).toEqual(['Review'])
  expect(tagsField.prop('format')(undefined)).toEqual([])

  expect(tagsField.prop('parse')(['Review'])).toEqual([{ name: 'Review' }])
  expect(tagsField.prop('parse')(undefined)).toEqual([])

  expect(tagsField.prop('validate')(['Review'])).toBeUndefined()
  expect(tagsField.prop('validate')([])).toEqual('Required')
})

test('opens the manual SV modal and exercises the form field callbacks', () => {
  const store = configureStore({
    ...STATE_WITH_2_FAMILIES,
    savedVariantFamilies: { F011652_1: { loaded: true } },
    modal: { 'F011652_1-addVariant-SV': { open: true } },
  })
  const wrapper = mount(
    <Provider store={store}>
      <CreateVariantButtons family={FAMILY} />
    </Provider>,
  )

  const zygosityFields = wrapper.find('ForwardRef(Field)[name^="genotypes."]')
  expect(zygosityFields.length).toBeGreaterThan(0)
  const zygosityField = zygosityFields.first()
  expect(zygosityField.prop('parse')(2)).toEqual({ cn: 2 })
  expect(zygosityField.prop('format')({ cn: 2 })).toBe(2)
  expect(zygosityField.prop('format')(undefined)).toBeUndefined()
})

test('opens the manual SNV modal for a family with no tagged saved variants', () => {
  const store = configureStore({
    ...STATE_WITH_2_FAMILIES,
    savedVariantsByGuid: {},
    savedVariantFamilies: { F011652_1: { loaded: true } },
    modal: { 'F011652_1-addVariant-Variant': { open: true } },
  })
  const wrapper = mount(
    <Provider store={store}>
      <CreateVariantButtons family={FAMILY} />
    </Provider>,
  )

  expect(wrapper.find('ForwardRef(Field)[name^="genotypes."]').length).toBeGreaterThan(0)
})

test('renders nothing when the project is not editable and the user is not an analyst', () => {
  const readOnlyState = {
    ...STATE_WITH_2_FAMILIES,
    projectsByGuid: {
      ...STATE_WITH_2_FAMILIES.projectsByGuid,
      R0237_1000_genomes_demo: { ...STATE_WITH_2_FAMILIES.projectsByGuid.R0237_1000_genomes_demo, canEdit: false },
    },
  }
  const store = configureStore(readOnlyState)
  const wrapper = mount(
    <Provider store={store}>
      <CreateVariantButtons family={FAMILY} />
    </Provider>
  )

  expect(wrapper.text()).toEqual('')
})

test('renders buttons for a non-editable project when the user is an analyst on an analyst project', () => {
  const analystState = {
    ...STATE_WITH_2_FAMILIES,
    user: { ...STATE_WITH_2_FAMILIES.user, isAnalyst: true },
    projectsByGuid: {
      ...STATE_WITH_2_FAMILIES.projectsByGuid,
      R0237_1000_genomes_demo: {
        ...STATE_WITH_2_FAMILIES.projectsByGuid.R0237_1000_genomes_demo, canEdit: false, isAnalystProject: true,
      },
    },
  }
  const store = configureStore(analystState)
  const wrapper = mount(
    <Provider store={store}>
      <CreateVariantButtons family={FAMILY} />
    </Provider>
  )

  expect(wrapper.text()).toContain('Add Manual Variant')
  expect(wrapper.text()).toContain('Add Manual SV')
})

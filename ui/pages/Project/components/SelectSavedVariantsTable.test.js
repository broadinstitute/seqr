import React from 'react'
import { mount, configure } from 'enzyme'
import Adapter from '@wojtekmaj/enzyme-adapter-react-17'
import configureStore from 'redux-mock-store'
import thunk from 'redux-thunk'
import { Provider } from 'react-redux'

import SelectSavedVariantsTable, { GENES_COLUMN, VARIANT_POS_COLUMN, TAG_COLUMN } from './SelectSavedVariantsTable'
import { STATE_WITH_2_FAMILIES } from '../fixtures'

configure({ adapter: new Adapter() })

const { alt, chrom, pos, ref, tagGuids, geneIds, variantGuid } = STATE_WITH_2_FAMILIES.savedVariantsByGuid.SV0000004_116042722_r0390_1000
const VARIANT = {
  variantGuid,
  chrom,
  pos,
  ref,
  alt,
  genes: geneIds.map(geneId => STATE_WITH_2_FAMILIES.genesById[geneId]),
  tags: tagGuids.map(tagGuid => STATE_WITH_2_FAMILIES.variantTagsByGuid[tagGuid]),
}

test('renders variant position, genes, and tags columns', () => {
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <SelectSavedVariantsTable
        familyGuid="F011652_1"
        idField="variantGuid"
        data={[VARIANT]}
        columns={[GENES_COLUMN, VARIANT_POS_COLUMN, TAG_COLUMN]}
      />
    </Provider>
  )

  expect(wrapper.text()).toContain('OR2M3')
  expect(wrapper.text()).toContain('22:45919065 TTTC > T')
  expect(wrapper.find('ColoredLabel').prop('content')).toEqual('Review')
  expect(wrapper.find('ColoredLabel').prop('color')).toEqual('#668FE3')
})

test('renders a deletion variant summary and handles missing genes', () => {
  const deletionVariant = {
    ...VARIANT, variantGuid: 'SV_deletion', alt: null, end: 116043000, genes: null,
  }
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <SelectSavedVariantsTable
        familyGuid="F011652_1"
        idField="variantGuid"
        data={[deletionVariant]}
        columns={[GENES_COLUMN, VARIANT_POS_COLUMN, TAG_COLUMN]}
      />
    </Provider>
  )

  expect(wrapper.text()).toContain(`22:${pos} -116043000`)
})

test('handles a null gene within a variant\'s genes list', () => {
  const variantWithNullGene = { ...VARIANT, variantGuid: 'SV_null_gene', genes: [null] }
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <SelectSavedVariantsTable
        familyGuid="F011652_1"
        idField="variantGuid"
        data={[variantWithNullGene]}
        columns={[GENES_COLUMN, VARIANT_POS_COLUMN, TAG_COLUMN]}
      />
    </Provider>
  )

  expect(wrapper.find('tbody tr').length).toEqual(1)
})

test('selects a row when clicked and calls onChange with the selection', () => {
  const onChange = jest.fn()
  const store = configureStore([thunk])(STATE_WITH_2_FAMILIES)
  const wrapper = mount(
    <Provider store={store}>
      <SelectSavedVariantsTable
        familyGuid="F011652_1"
        idField="variantGuid"
        data={[VARIANT]}
        columns={[GENES_COLUMN, VARIANT_POS_COLUMN, TAG_COLUMN]}
        onChange={onChange}
      />
    </Provider>
  )

  wrapper.find('tbody tr').first().simulate('click')

  expect(onChange).toHaveBeenCalledWith({ SV0000004_116042722_r0390_1000: true })
})

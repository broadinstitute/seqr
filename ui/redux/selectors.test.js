/* eslint-disable no-undef */

import { STATE_WITH_2_FAMILIES } from 'pages/Project/fixtures'
import {
  getVariantTagNotesByFamilyVariants,
  getSelectableTagTypesByProject,
  getUserOptions,
  getLocusListIntervalsByChromProject,
  getSpliceOutliersByChromFamily,
  getProjectAnalysisGroupFamilyGuidsByGuid,
} from './selectors'
import {DYNAMIC_ANALYSIS_GROUP_GUID, FAMILY_GUID, GENE_ID, SEARCH, SEARCH_HASH, STATE} from "../pages/Search/fixtures";

test('getVariantTagNotesByByFamilyVariants', () => {
  const tagsNotesByGuid = getVariantTagNotesByFamilyVariants(
    STATE_WITH_2_FAMILIES,
  )
  expect(Object.keys(tagsNotesByGuid).length).toEqual(2)
  expect(Object.keys(tagsNotesByGuid.F011652_1).length).toEqual(3)
  expect(tagsNotesByGuid.F011652_1['22-45919065-TTTC-T'].notes.length).toEqual(1)
  expect(tagsNotesByGuid.F011652_1['22-45919065-TTTC-T'].tags.length).toEqual(1)
  expect(tagsNotesByGuid.F011652_1['1-248367227-TC-T'].tags.length).toEqual(2)
  expect(tagsNotesByGuid.F011652_1['batch_123_DEL'].tags).toEqual(undefined)
  expect(Object.keys(tagsNotesByGuid.F011652_2).length).toEqual(3)
  expect(tagsNotesByGuid.F011652_2['22-248367227-C-T']).toEqual({ variantGuids: 'SV0000003_2246859832_r0390_100'})
  expect(tagsNotesByGuid.F011652_2['22-248367228-C-T']).toEqual({ variantGuids: 'SV0000005_2246859833_r0390_100'})
  expect(tagsNotesByGuid.F011652_2['22-248367227-C-T,22-248367228-C-T'].tags.length).toEqual(1)
})

test('getSelectableTagTypesByProject', () => {
  expect(getSelectableTagTypesByProject(STATE, {})).toEqual(
    { R0237_1000_genomes_demo: [] },
  )
})

test('getUserOptions', () => {
  const options = getUserOptions(STATE_WITH_2_FAMILIES)
  expect(Object.keys(options).length).toEqual(7)
  expect(options[1]).toEqual({ key: '4MW8vPtmHG', value: '4MW8vPtmHG', text: 'Mekdes (mgetaneh@broadinstitute.org)'})
})

test('getLocusListIntervalsByChromProject', () => {
  expect(getLocusListIntervalsByChromProject(STATE, {})).toEqual({
    ['1']: {
      'R0237_1000_genomes_demo': [
        {'chrom': '1', 'end': 7300, 'genomeVersion': '37', 'locusListGuid': 'LL00132_2017_monogenic_ibd_gen', 'locusListIntervalGuid': 'LLI0000012_test_list_edit4545_', 'start': 7200},
      ],
    },
    ['3']: {
      'R0237_1000_genomes_demo': [
        {'chrom': '3', 'end': 3000, 'genomeVersion': '37', 'locusListGuid': 'LL00132_2017_monogenic_ibd_gen', 'locusListIntervalGuid': 'LLI0000013_a_new_list325_3000', 'start': 25},
      ],
    }
  })
})

test('getSpliceOutliersByChromFamily', () => {
  expect(getSpliceOutliersByChromFamily(STATE, {})).toEqual({
    ['10']: {
      'F011652_1': [
        {
          familyGuid: "F011652_1", geneSymbol: "ENSG00000136758", idField: "ENSG00000136758-10-27114300-27114400-*-psi5", individualGuid: "I021474_na19679", individualName: "",
          chrom: "10", deltaPsi: 0.56, end: 27114400, geneId: "ENSG00000136758", isSignificant: true, pValue: 2.1234e-10, rareDiseaseSamplesTotal: 171, rareDiseaseSamplesWithJunction: 1, readCount: 1208, start: 27114300, strand: "*", tissueType: "F", type: "psi5", zScore: 2.96,
        },
      ],
    },
    ['11']: {
      'F011652_1': [
        {
          familyGuid: "F011652_1", geneSymbol: "ENSG00000136758", idField: "ENSG00000136758-11-27114300-27114400-*-psi5", individualGuid: "I021474_na19679", individualName: "",
          chrom: "11", deltaPsi: 0.56, end: 27114400, geneId: "ENSG00000136758", isSignificant: true, pValue: 2.1234e-10, rareDiseaseSamplesTotal: 171, rareDiseaseSamplesWithJunction: 1, readCount: 1208, start: 27114300, strand: "*", tissueType: "F", type: "psi5", zScore: 2.96,
        },
      ],
    }
  })
})

test('getProjectAnalysisGroupFamilyGuidsByGuid', () => {
  expect(getProjectAnalysisGroupFamilyGuidsByGuid(STATE, { projectGuid: 'R0237_1000_genomes_demo' })).toEqual({
    AG0000183_test_group: ['F011652_1'],
    DAG0000183_test: ['F011652_1'],
    DAG0000184_test_2: [],
  })
  expect(getProjectAnalysisGroupFamilyGuidsByGuid(STATE, {})).toEqual({
    DAG0000183_test: [],
  })
})

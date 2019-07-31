/* eslint-disable no-undef */

import orderBy from 'lodash/orderBy'
import { getVisibleFamilies, getVisibleFamiliesInSortedOrder, getFamiliesExportData, getIndividualsExportData,
  getCaseReviewStatusCounts, getProjectAnalysisGroupFamiliesByGuid, getIndividualTaggedVariants,
  getDefaultMmeSubmissionByIndividual, getMmeResultsByIndividual, getMmeDefaultContactEmail, getAnalystOptions
} from './selectors'

import { STATE_WITH_2_FAMILIES } from './fixtures'

test('getVisibleFamilies', () => {

  const visibleFamilies = getVisibleFamilies(STATE_WITH_2_FAMILIES, {})

  expect(visibleFamilies.length).toEqual(2)
  expect(visibleFamilies[0].familyGuid).toEqual('F011652_1')
  expect(visibleFamilies[1].familyGuid).toEqual('F011652_2')
})

test('getVisibleFamiliesInSortedOrder', () => {
  const visibleFamiliesSorted = getVisibleFamiliesInSortedOrder(STATE_WITH_2_FAMILIES, {})

  expect(visibleFamiliesSorted.length).toEqual(2)
  expect(visibleFamiliesSorted[0].familyGuid).toEqual('F011652_2')
  expect(visibleFamiliesSorted[1].familyGuid).toEqual('F011652_1')
})


test('getFamiliesExportData', () => {
  const exportFamilies = getFamiliesExportData(STATE_WITH_2_FAMILIES, {})

  expect(exportFamilies.length).toEqual(2)
  expect(exportFamilies[0].familyGuid).toEqual('F011652_2')
  expect(exportFamilies[1].familyGuid).toEqual('F011652_1')
  expect(exportFamilies[0].firstSample.sampleGuid).toEqual('S2310656_wal_mc16200_mc16203')
  expect(exportFamilies[1].firstSample).toEqual(null)
})

test('getIndividualsExportData', () => {
  const exportIndividuals = getIndividualsExportData(STATE_WITH_2_FAMILIES, {})

  expect(exportIndividuals.length).toEqual(6)
  expect(exportIndividuals.map(individual => individual.individualId)).toEqual([
    'NA19675', 'NA19678', 'NA19679', 'NA19675', 'NA19678', 'NA19679',
  ])
  expect(exportIndividuals[1].familyId).toEqual('2')
  expect(exportIndividuals[1].hasLoadedSamples).toEqual(true)
  expect(exportIndividuals[3].familyId).toEqual('1')
  expect(exportIndividuals[3].hasLoadedSamples).toEqual(false)
})

test('getCaseReviewStatusCounts', () => {
  const caseReviewStatusCounts = getCaseReviewStatusCounts(STATE_WITH_2_FAMILIES)
  const caseReviewStatusCountsSorted = orderBy(caseReviewStatusCounts, [obj => obj.count], 'desc')

  expect(caseReviewStatusCountsSorted.length).toEqual(8)

  expect(caseReviewStatusCountsSorted[0]).toHaveProperty('name', 'In Review')
  expect(caseReviewStatusCountsSorted[0]).toHaveProperty('value', 'I')
  expect(caseReviewStatusCountsSorted[0]).toHaveProperty('count', 4)


  expect(caseReviewStatusCountsSorted[1]).toHaveProperty('name', 'Accepted')
  expect(caseReviewStatusCountsSorted[1]).toHaveProperty('value', 'A')
  expect(caseReviewStatusCountsSorted[1]).toHaveProperty('count', 2)

  expect(caseReviewStatusCountsSorted[2]).toHaveProperty('count', 0)

})

test('getProjectAnalysisGroupFamiliesByGuid', () => {

  const families = getProjectAnalysisGroupFamiliesByGuid.resultFunc(
    STATE_WITH_2_FAMILIES.familiesByGuid, STATE_WITH_2_FAMILIES.analysisGroupsByGuid, 'AG0000183_test_group',
  )

  expect(Object.keys(families)).toEqual(['F011652_1'])
  expect(families.F011652_1.familyId).toEqual('1')
})

test('getIndividualTaggedVariants', () => {
  const individualVariants = getIndividualTaggedVariants(STATE_WITH_2_FAMILIES, { individualGuid: 'I021475_na19675_1' })
  expect(individualVariants.length).toEqual(2)
  expect(individualVariants[0].variantGuid).toEqual('SV0000004_116042722_r0390_1000')
  expect(individualVariants[0].variantId).toEqual('22-45919065-TTTC-T')
  expect(individualVariants[0].numAlt).toEqual(2)
  expect(individualVariants[0].gq).toEqual(99)
  expect(individualVariants[0].geneSymbol).toEqual('OR2M3')
})

test('getDefaultMmeSubmissionByIndividual', () => {
  const defaultSubmissions = getDefaultMmeSubmissionByIndividual(STATE_WITH_2_FAMILIES, { match: { params:  {} } })
  expect(Object.keys(defaultSubmissions).length).toEqual(6)
  expect(defaultSubmissions.I021475_na19675_1).toEqual({
    patient: {
      contact: {
        name: 'PI',
        institution: 'Broad',
        href: 'test@broadinstitute.org',
      },
      species: 'NCBITaxon:9606',
      sex: 'MALE',
      id: 'NA19675',
      label: 'NA19675',
    },
    geneVariants: [],
    phenotypes: [],
  })
})

test('getMmeResultsByIndividual', () => {
  const mmeResults = getMmeResultsByIndividual(STATE_WITH_2_FAMILIES, {match: {params: {}}})
  expect(Object.keys(mmeResults).length).toEqual(6)
  expect(mmeResults.I021475_na19675_1.active.length).toEqual(1)
  expect(mmeResults.I021475_na19675_1.active[0].id).toEqual('12531')
  expect(mmeResults.I021475_na19675_1.active[0].geneVariants.length).toEqual(1)
  expect(mmeResults.I021475_na19675_1.active[0].comments).toEqual('This seems promising')
  expect(mmeResults.I021475_na19675_1.active[0].matchStatus.comments).toEqual('This seems promising')

  expect(mmeResults.I021475_na19675_1.removed.length).toEqual(1)
  expect(mmeResults.I021475_na19675_1.removed[0].id).toEqual('10509')
})

test('getMmeDefaultContactEmail', () => {
  expect(getMmeDefaultContactEmail(STATE_WITH_2_FAMILIES, { matchmakerResultGuid: 'MR0005038_HK018_0047' })).toEqual({
    matchmakerResultGuid: 'MR0005038_HK018_0047',
    patientId: '12531',
    to: 'crowley@unc.edu,test@test.com,test@broadinstitute.org',
    subject: 'OR2M3 Matchmaker Exchange connection (NA19675_1)',
    body: 'Dear James Crowley,\n\nWe recently matched with one of your patients in Matchmaker Exchange harboring a variant in OR2M3. Our patient has a homozygous missense variant 1:248367227 TC>T and presents with childhood onset short-limb short stature and flexion contracture. Would you be willing to share whether your patient\'s phenotype and genotype match with ours? We are very grateful for your help and look forward to hearing more.\n\nBest wishes,\nTest User',
  })
})

test('getAnalystOptions', () => {
  const analystOptions = getAnalystOptions(STATE_WITH_2_FAMILIES)
  expect(Object.keys(analystOptions).length).toEqual(6)
  expect(analystOptions[0].value).toEqual('test_user1')
})

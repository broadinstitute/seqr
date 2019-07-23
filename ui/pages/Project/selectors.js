import orderBy from 'lodash/orderBy'
import mapValues from 'lodash/mapValues'
import { createSelector } from 'reselect'


import { getSearchResults } from 'redux/utils/reduxSearchEnhancer'
import {
  FAMILY_ANALYSIS_STATUS_OPTIONS,
  FAMILY_FIELD_ID,
  INDIVIDUAL_FIELD_ID,
  FAMILY_FIELD_FIRST_SAMPLE,
  SEX_LOOKUP,
  SHOW_ALL,
  latestSamplesLoaded,
  familySamplesLoaded,
} from 'shared/utils/constants'
import { toCamelcase, toSnakecase } from 'shared/utils/stringUtils'

import {
  getCurrentProject, getFamiliesGroupedByProjectGuid, getIndividualsByGuid, getSamplesByGuid, getGenesById, getUser,
  getAnalysisGroupsGroupedByProjectGuid, getSavedVariantsByGuid, getFirstSampleByFamily, getSortedIndividualsByFamily,
  getMmeResultsByGuid, getProjectGuid, getAllUsers,
} from 'redux/selectors'

import {
  SORT_BY_FAMILY_NAME,
  CASE_REVIEW_STATUS_OPTIONS,
  FAMILY_FILTER_LOOKUP,
  FAMILY_SORT_OPTIONS,
  FAMILY_EXPORT_DATA,
  INTERNAL_FAMILY_EXPORT_DATA,
  INDIVIDUAL_HAS_DATA_FIELD,
  INDIVIDUAL_EXPORT_DATA,
  INTERNAL_INDIVIDUAL_EXPORT_DATA,
  SAMPLE_EXPORT_DATA,
} from './constants'

const FAMILY_SORT_LOOKUP = FAMILY_SORT_OPTIONS.reduce(
  (acc, opt) => ({
    ...acc,
    [opt.value]: opt.createSortKeyGetter,
  }), {},
)

// project data selectors

export const getProjectDetailsIsLoading = state => state.projectDetailsLoading.isLoading
export const getMatchmakerMatchesLoading = state => state.matchmakerMatchesLoading.isLoading
export const getMatchmakerContactNotes = state => state.mmeContactNotes


const selectEntitiesForProjectGuid = (entitiesGroupedByProjectGuid, projectGuid) => entitiesGroupedByProjectGuid[projectGuid] || {}
export const getProjectFamiliesByGuid = createSelector(getFamiliesGroupedByProjectGuid, getProjectGuid, selectEntitiesForProjectGuid)
export const getProjectAnalysisGroupsByGuid = createSelector(getAnalysisGroupsGroupedByProjectGuid, getProjectGuid, selectEntitiesForProjectGuid)

export const getProjectAnalysisGroupFamiliesByGuid = createSelector(
  getProjectFamiliesByGuid,
  getProjectAnalysisGroupsByGuid,
  (state, props) => (props.match ? props.match.params.analysisGroupGuid : props.analysisGroupGuid),
  (projectFamiliesByGuid, projectAnalysisGroupsByGuid, analysisGroupGuid) => {
    if (!analysisGroupGuid || !projectAnalysisGroupsByGuid[analysisGroupGuid]) {
      return projectFamiliesByGuid
    }
    return projectAnalysisGroupsByGuid[analysisGroupGuid].familyGuids.reduce(
      (acc, familyGuid) => ({ ...acc, [familyGuid]: projectFamiliesByGuid[familyGuid] }), {},
    )
  },
)

export const getProjectAnalysisGroupIndividualsByGuid = createSelector(
  getIndividualsByGuid,
  getProjectAnalysisGroupFamiliesByGuid,
  (individualsByGuid, familiesByGuid) =>
    Object.values(familiesByGuid).reduce((acc, family) => ({
      ...acc,
      ...family.individualGuids.reduce((indivAcc, individualGuid) => (
        { ...indivAcc, [individualGuid]: { ...individualsByGuid[individualGuid], [FAMILY_FIELD_ID]: family.familyId } }
      ), {}),
    }), {}),
)

export const getProjectAnalysisGroupSamplesByGuid = createSelector(
  getSamplesByGuid,
  getProjectAnalysisGroupIndividualsByGuid,
  (samplesByGuid, individualsByGuid) =>
    Object.values(individualsByGuid).reduce((acc, individual) => ({
      ...acc,
      ...individual.sampleGuids.reduce((sampleAcc, sampleGuid) => (
        { ...sampleAcc, [sampleGuid]: samplesByGuid[sampleGuid] }
      ), {}),
    }), {}),
)


export const getIndividualTaggedVariants = createSelector(
  getSavedVariantsByGuid,
  getIndividualsByGuid,
  getGenesById,
  (state, props) => props.individualGuid,
  (savedVariants, individualsByGuid, genesById, individualGuid) => {
    const { familyGuid } = individualsByGuid[individualGuid]
    return Object.values(savedVariants).filter(
      o => o.familyGuids.includes(familyGuid) && o.tags.length).map(variant => ({
      ...variant,
      variantId: `${variant.chrom}-${variant.pos}-${variant.ref}-${variant.alt}`,
      ...variant.genotypes[individualGuid],
      ...genesById[variant.mainTranscript.geneId],
    }))
  },
)

// Family table selectors
export const getFamiliesTableState = createSelector(
  (state, ownProps) => state[`${toCamelcase((ownProps || {}).tableName) || 'family'}TableState`],
  tableState => tableState,
)
export const getFamiliesFilter = createSelector(
  getFamiliesTableState,
  familyTableState => familyTableState.familiesFilter || SHOW_ALL,
)
export const getFamiliesSortOrder = createSelector(
  getFamiliesTableState,
  familyTableState => familyTableState.familiesSortOrder || SORT_BY_FAMILY_NAME,
)
export const getFamiliesSortDirection = createSelector(
  getFamiliesTableState,
  familyTableState => familyTableState.familiesSortDirection || 1,
)

/**
 * function that returns an array of family guids that pass the currently-selected
 * familiesFilter.
 *
 * @param state {object} global Redux state
 */
export const getVisibleFamilies = createSelector(
  getProjectAnalysisGroupFamiliesByGuid,
  getIndividualsByGuid,
  getSamplesByGuid,
  getUser,
  getFamiliesFilter,
  getSearchResults('familiesByGuid'),
  (familiesByGuid, individualsByGuid, samplesByGuid, user, familiesFilter, familySearchResults) => {
    const searchedFamilies = familySearchResults.map(family => familiesByGuid[family]).filter(family => family)

    if (!familiesFilter || !FAMILY_FILTER_LOOKUP[familiesFilter]) {
      return searchedFamilies
    }

    const familyFilter = FAMILY_FILTER_LOOKUP[familiesFilter].createFilter(individualsByGuid, samplesByGuid, user)
    return searchedFamilies.filter(familyFilter)
  },
)


/**
 * function that returns an array of currently-visible family objects, sorted according to
 * currently-selected values of familiesSortOrder and familiesSortDirection.
 *
 * @param state {object} global Redux state
 */
export const getVisibleFamiliesInSortedOrder = createSelector(
  getVisibleFamilies,
  getIndividualsByGuid,
  getSamplesByGuid,
  getFamiliesSortOrder,
  getFamiliesSortDirection,
  (visibleFamilies, individualsByGuid, samplesByGuid, familiesSortOrder, familiesSortDirection) => {
    if (!familiesSortOrder || !FAMILY_SORT_LOOKUP[familiesSortOrder]) {
      return visibleFamilies
    }

    const getSortKey = FAMILY_SORT_LOOKUP[familiesSortOrder](individualsByGuid, samplesByGuid)

    return orderBy(visibleFamilies, [getSortKey], [familiesSortDirection > 0 ? 'asc' : 'desc'])
  },
)

export const getEntityExportConfig = (project, rawData, tableName, fileName, fields) => ({
  filename: `${project.name.replace(' ', '_').toLowerCase()}_${tableName ? `${toSnakecase(tableName)}_` : ''}${fileName}`,
  rawData,
  headers: fields.map(config => config.header),
  processRow: family => fields.map((config) => {
    const val = family[config.field]
    return config.format ? config.format(val) : val
  }),
})

export const getFamiliesExportData = createSelector(
  getVisibleFamiliesInSortedOrder,
  getFirstSampleByFamily,
  (visibleFamilies, firstSampleByFamily) =>
    visibleFamilies.reduce((acc, family) =>
      [...acc, { ...family, [FAMILY_FIELD_FIRST_SAMPLE]: firstSampleByFamily[family.familyGuid] }], []),
)

export const getFamiliesExportConfig = createSelector(
  getCurrentProject,
  getFamiliesExportData,
  (state, ownProps) => (ownProps || {}).tableName,
  () => 'families',
  (state, ownProps) => ((ownProps || {}).internal ? FAMILY_EXPORT_DATA.concat(INTERNAL_FAMILY_EXPORT_DATA) : FAMILY_EXPORT_DATA),
  getEntityExportConfig,
)

export const getIndividualsExportData = createSelector(
  getVisibleFamiliesInSortedOrder,
  getSortedIndividualsByFamily,
  getSamplesByGuid,
  (families, individualsByFamily, samplesByGuid) => families.reduce((acc, family) =>
    [...acc, ...individualsByFamily[family.familyGuid].map(individual => ({
      ...individual,
      [FAMILY_FIELD_ID]: family.familyId,
      [INDIVIDUAL_HAS_DATA_FIELD]: latestSamplesLoaded(individual.sampleGuids, samplesByGuid).length > 0,
    }))], [],
  ),
)

export const getIndividualsExportConfig = createSelector(
  getCurrentProject,
  getIndividualsExportData,
  (state, ownProps) => (ownProps || {}).tableName,
  () => 'individuals',
  (state, ownProps) => ((ownProps || {}).internal ? INDIVIDUAL_EXPORT_DATA.concat(INTERNAL_INDIVIDUAL_EXPORT_DATA) : INDIVIDUAL_EXPORT_DATA),
  getEntityExportConfig,
)

const getSamplesExportData = createSelector(
  getVisibleFamiliesInSortedOrder,
  getIndividualsByGuid,
  getSamplesByGuid,
  (visibleFamilies, individualsByGuid, samplesByGuid) =>
    visibleFamilies.reduce((acc, family) =>
      [...acc, ...familySamplesLoaded(family, individualsByGuid, samplesByGuid).map(sample => ({
        ...sample,
        [FAMILY_FIELD_ID]: family.familyId,
        [INDIVIDUAL_FIELD_ID]: individualsByGuid[sample.individualGuid].individualId,
      }))], []),
)

export const getSamplesExportConfig = createSelector(
  getCurrentProject,
  getSamplesExportData,
  (state, ownProps) => (ownProps || {}).tableName,
  () => 'samples',
  () => SAMPLE_EXPORT_DATA,
  getEntityExportConfig,
)

export const getCaseReviewStatusCounts = createSelector(
  getProjectGuid,
  getIndividualsByGuid,
  (projectGuid, individualsByGuid) => {
    const caseReviewStatusCounts = Object.values(individualsByGuid).reduce((acc, individual) => (
      individual.projectGuid === projectGuid ?
        { ...acc, [individual.caseReviewStatus]: (acc[individual.caseReviewStatus] || 0) + 1 } : acc
    ), {})

    return CASE_REVIEW_STATUS_OPTIONS.map(option => (
      { ...option, count: (caseReviewStatusCounts[option.value] || 0) }),
    )
  })

export const getAnalysisStatusCounts = createSelector(
  getProjectAnalysisGroupFamiliesByGuid,
  (familiesByGuid) => {
    const analysisStatusCounts = Object.values(familiesByGuid).reduce((acc, family) => ({
      ...acc, [family.analysisStatus]: (acc[family.analysisStatus] || 0) + 1,
    }), {})

    return FAMILY_ANALYSIS_STATUS_OPTIONS.map(option => (
      { ...option, count: (analysisStatusCounts[option.value] || 0) }),
    )
  })

export const getDefaultMmeSubmissionByIndividual = createSelector(
  getCurrentProject,
  getProjectAnalysisGroupIndividualsByGuid,
  (project, individualsByGuid) => mapValues(individualsByGuid, individual => ({
    patient: {
      contact: {
        name: project.mmePrimaryDataOwner,
        institution: project.mmeContactInstitution,
        href: project.mmeContactUrl,
      },
      species: 'NCBITaxon:9606',
      sex: SEX_LOOKUP[individual.sex].toUpperCase(),
      id: individual.individualId,
      label: individual.individualId,
    },
    geneVariants: [],
    phenotypes: [],
  })),
)

export const getMmeResultsByIndividual = createSelector(
  getMmeResultsByGuid,
  getProjectAnalysisGroupIndividualsByGuid,
  (mmeResultsByGuid, individualsByGuid) =>
    mapValues(individualsByGuid, individual => (individual.mmeResultGuids || []).reduce((acc, resultGuid) => {
      const result = {
        ...mmeResultsByGuid[resultGuid].matchStatus,
        ...mmeResultsByGuid[resultGuid],
      }
      if (result.matchRemoved || individual.mmeDeletedDate) {
        acc.removed.push(result)
      }
      else {
        acc.active.push(result)
      }
      return acc
    }, { active: [], removed: [] })),
)

export const getMmeDefaultContactEmail = createSelector(
  getMmeResultsByGuid,
  getIndividualsByGuid,
  getGenesById,
  getSavedVariantsByGuid,
  getUser,
  (state, ownProps) => ownProps.matchmakerResultGuid,
  (mmeResultsByGuid, individualsByGuid, genesById, savedVariants, user, matchmakerResultGuid) => {
    const { patient, geneVariants, individualGuid } = mmeResultsByGuid[matchmakerResultGuid]
    const geneName = geneVariants && geneVariants.length && (genesById[geneVariants[0].geneId] || {}).geneSymbol

    const { mmeSubmittedData, familyGuid } = individualsByGuid[individualGuid]

    const submittedGenes = [...new Set((mmeSubmittedData.geneVariants || []).map(
      ({ geneId }) => (genesById[geneId] || {}).geneSymbol))].join(', ')

    Object.values(savedVariants).filter(
      o => o.familyGuids.includes(familyGuid) && o.tags.length).map(variant => ({
      ...variant,
      variantId: `${variant.chrom}-${variant.pos}-${variant.ref}-${variant.alt}`,
      ...variant.genotypes[individualGuid],
      ...genesById[variant.mainTranscript.geneId],
    }))

    const submittedVariants = (mmeSubmittedData.geneVariants || []).map(({ alt, ref, chrom, pos }) => {
      const savedVariant = Object.values(savedVariants).find(
        o => o.chrom === chrom && o.pos === pos && o.ref === ref && o.alt === alt
          && o.familyGuids.includes(familyGuid)) || {}
      const genotype = (savedVariant.genotypes || {})[individualGuid] || {}
      const mainTranscript = savedVariant.mainTranscript || {}
      const consequence = (mainTranscript.majorConsequence || '').replace(/_variant/g, '').replace(/_/g, ' ')
      const hgvs = [(mainTranscript.hgvsc || '').split(':').pop(), (mainTranscript.hgvsp || '').split(':').pop()].filter(val => val).join('/')

      return `a ${genotype.numAlt === 1 ? 'heterozygous' : 'homozygous'} ${consequence} variant ${chrom}:${pos} ${ref}>${alt}${hgvs ? ` (${hgvs})` : ''}`
    }).join(', ')

    const submittedPhenotypeList = (mmeSubmittedData.phenotypes || []).filter(
      ({ observed, label }) => observed === 'yes' && label).map(({ label }) => label.toLowerCase())
    const numPhenotypes = submittedPhenotypeList.length
    if (numPhenotypes > 2) {
      submittedPhenotypeList[numPhenotypes - 1] = `and ${submittedPhenotypeList[numPhenotypes - 1]}`
    }
    const submittedPhenotypes = submittedPhenotypeList.join(numPhenotypes === 2 ? ' and ' : ', ')

    const contacts = [
      patient.contact.href.replace('mailto:', ''),
      mmeSubmittedData.patient.contact.href.replace('mailto:', '').replace('matchmaker@broadinstitute.org,', ''),
      user.email,
    ]
    return {
      matchmakerResultGuid,
      patientId: patient.id,
      to: contacts.filter(val => val).join(','),
      subject: `${geneName || `Patient ${patient.id}`} Matchmaker Exchange connection (${mmeSubmittedData.patient.id})`,
      body: `Dear ${patient.contact.name},\n\nWe recently matched with one of your patients in Matchmaker Exchange harboring ${(mmeSubmittedData.geneVariants || []).length === 1 ? 'a variant' : 'variants'} in ${submittedGenes}. Our patient has ${submittedVariants}${submittedPhenotypes ? ` and presents with ${submittedPhenotypes}` : ''}. Would you be willing to share whether your patient's phenotype and genotype match with ours? We are very grateful for your help and look forward to hearing more.\n\nBest wishes,\n${user.displayName}`,
    }
  },
)


// user options selectors
export const getUserOptions = createSelector(
  getAllUsers,
  users => users.map(
    user => ({ key: user.username, value: user.username, text: user.email }),
  ),
)

export const getCollaborators = createSelector(
  getCurrentProject,
  project => project.collaborators,
)

// analyst option selectors (add project collaborators to staff users)
export const getAnalystOptions = createSelector(
  getCollaborators,
  getAllUsers,
  (collaborators, users) => {
    const staff = users.filter(user => user.isStaff)
    const uniqueCollaborators = collaborators.filter(collaborator => !collaborator.isStaff)
    return [...uniqueCollaborators, ...staff].map(
      user => ({ key: user.username, value: user.username, text: user.email }),
    )
  },
)

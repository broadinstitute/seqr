import { createSelector } from 'reselect'

import { getSortedIndividualsByFamily, getGenesById, getUser } from 'redux/selectors'
import { getVariantMainGeneId, getVariantSummary } from 'shared/utils/constants'

export const getSuccessStoryLoading = state => state.successStoryLoading.isLoading
export const getSuccessStoryLoadingError = state => state.successStoryLoading.errorMessage
export const getSuccessStoryRows = state => state.successStoryRows
export const getMmeLoading = state => state.mmeLoading.isLoading
export const getMmeLoadingError = state => state.mmeLoading.errorMessage
export const getMmeMetrics = state => state.mmeMetrics
export const getMmeSubmissions = state => state.mmeSubmissions
export const getExternalAnalysisUploadStats = state => state.externalAnalysisUploadStats

export const getVlmFamiliesByContactEmail = createSelector(
  getSortedIndividualsByFamily,
  (state, ownProps) => ownProps.variant,
  (individualsByFamily, variant) => (variant.lookupFamilyGuids || []).reduce((acc, familyGuid) => {
    const individual = individualsByFamily[familyGuid]?.[0]
    const contactEmail = individual?.projectGuid ? 'internal' : (individual?.vlmContactEmail || 'disabled')
    return { ...acc, [contactEmail]: [...(acc[contactEmail] || []), familyGuid] }
  }, {}),
)

export const getVlmDefaultContactEmails = createSelector(
  getVlmFamiliesByContactEmail,
  getGenesById,
  getUser,
  (state, ownProps) => ownProps.variant,
  (familiesByContactEmail, genesById, user, variant) => {
    const gene = genesById[getVariantMainGeneId(variant)]?.geneSymbol
    const subject = `${gene || variant.variantId} variant match in seqr`
    const defaultEmailContent = `harboring ${getVariantSummary(variant)} in ${gene || 'no genes'} (${window.location.href}).
    \n\nWe have identified the variant in a case with [replace with phenotype].
    \n\n[List your specific questions for the researcher here.]
    \n\nWe appreciate your assistance and look forward to hearing more from you.\n\nBest wishes,\n${user.displayName}`
    return Object.entries(familiesByContactEmail).reduce((acc, [to, familyGuids]) => ({
      ...acc,
      [to]: { to, subject, body: `Dear researcher,\n\nWe are interested in learning more about your ${familyGuids.length} cases in seqr ${defaultEmailContent}` },
    }), {})
  },
)

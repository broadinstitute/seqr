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

export const geVlmDefaultContactEmailByFamily = createSelector(
  getSortedIndividualsByFamily,
  getGenesById,
  getUser,
  (state, ownProps) => ownProps.variant,
  (individualsByFamily, genesById, user, variant) => {
    const gene = genesById[getVariantMainGeneId(variant)]?.geneSymbol
    const defaultEmail = {
      subject: `${gene || variant.variantId} variant match in seqr`,
      //
      body: `Dear researcher,\n\nWe are interested in learning more about your case in seqr harboring ${getVariantSummary(variant)} in ${gene || 'no genes'} (${window.location.href}).\n\nWe appreciate your assistance and look forward to hearing more from you.\n\nBest wishes,\n${user.displayName}`,
    }
    return (variant.lookupFamilyGuids || []).reduce((acc, familyGuid) => {
      const individual = individualsByFamily[familyGuid]?.[0]
      if (!individual || individual.projectGuid) {
        return acc
      }
      return { ...acc, [familyGuid]: { ...defaultEmail, to: individual.vlmContactEmail } }
    }, {})
  },
)

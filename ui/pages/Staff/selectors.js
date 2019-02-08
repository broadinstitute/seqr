import { createSelector } from 'reselect'

export const getAnvilLoading = state => state.anvilLoading.isLoading
export const getAnvilRows = state => state.anvilRows

// TODO real selector
export const getFamilyMatchmakerSubmissions = createSelector(
  getAnvilRows,
  (state, props) => props.family,
  (matchmakerSubmissions, family) => {
    return Object.values(matchmakerSubmissions[family.projectGuid] || {}).filter(
      submission => submission.familyId === family.familyId,
    )
  },
)

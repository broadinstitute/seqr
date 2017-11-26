import { createSelector } from 'reselect'

import { getIndividualsByGuid } from 'shared/utils/commonSelectors'
import { getNameForCategoryHpoId } from 'shared/utils/hpoUtils'
import { getFamilyGuidToIndividuals } from '../utils/visibleFamiliesSelector'


/**
 * function that returns a mapping of familySize => number of families
 *
 * @param state {object} global Redux state
 */
export const getFamilySizeHistogram = createSelector(
  getFamilyGuidToIndividuals,
  (familyGuidToIndividuals) => {
    const familySizes = Object.values(familyGuidToIndividuals)
      .map(individualsInFamily => individualsInFamily.length)
      .reduce((acc, familySize) => (
        { ...acc, [familySize]: (acc[familySize] || 0) + 1 }
      ), {})
    return familySizes
  },
)

/**
 * function that returns a mapping of hpo categories => number of terms in those categories
 *
 * @param state {object} global Redux state
 */
export const getHpoTermHistogram = createSelector(
  getIndividualsByGuid,
  (individualsByGuid) => {
    const hpoTerms = Object.values(individualsByGuid)
      .filter(individuals => individuals.phenotipsData && individuals.phenotipsData.features)
      .map(individuals => individuals.phenotipsData.features)
      .reduce((acc, features) => {
        features.forEach((feature) => {
          if (feature.category) {
            const categoryName = getNameForCategoryHpoId(feature.category)
            acc[categoryName] = (acc[categoryName] || 0) + 1
          }
        })
        return acc
      }, {})
    return hpoTerms
  },
)

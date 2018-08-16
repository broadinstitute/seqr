import { createSelector } from 'reselect'

import { getSavedVariantsByGuid, getGenesById } from 'redux/selectors'
import { VARIANT_SORT_LOOKUP, EXCLUDED_TAG_NAME, getVariantsExportData } from 'shared/utils/constants'

export const getSearchedVariants = state => state.searchedVariants
export const getSearchedVariantsIsLoading = state => state.searchedVariantsLoading.isLoading
export const getSearchedVariantsErrorMessage = state => state.searchedVariantsLoading.errorMessage
export const getVariantSearchDisplay = state => state.variantSearchDisplay

export const getTotalVariantsCount = createSelector(
  getSearchedVariants,
  variants => variants.length,
)

export const getSortedFilteredSearchedVariants = createSelector(
  getSearchedVariants,
  getSavedVariantsByGuid,
  getVariantSearchDisplay,
  getGenesById,
  (searchedVariants, savedVariantsByGuid, variantSearchDisplay, genesById) => {
    let variants = searchedVariants.map(variant =>
      (variant.variantGuid ? savedVariantsByGuid[variant.variantGuid] : variant),
    )

    if (variantSearchDisplay.hideExcluded) {
      variants = variants.filter(variant =>
        variant.tags.every(t => t.name !== EXCLUDED_TAG_NAME),
      )
    }

    variants.sort((a, b) => {
      return VARIANT_SORT_LOOKUP[variantSearchDisplay.sortOrder](a, b, genesById) || a.xpos - b.xpos
    })
    return variants
  },
)

export const getSearchedVariantExportConfig = createSelector(
  getSortedFilteredSearchedVariants,
  variants => [{
    name: 'Variant Search Results',
    data: {
      filename: 'searched_variants',
      ...getVariantsExportData(variants),
    },
  }],
)

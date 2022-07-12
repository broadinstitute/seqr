import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { navigateSavedHashedSearch } from 'redux/rootReducer'
import { VEP_GROUP_SV, ANY_AFFECTED } from 'shared/utils/constants'
import { FREQUENCIES, THIS_CALLSET_FREQUENCY, SV_CALLSET_FREQUENCY } from '../panel/search/constants'
import { ButtonLink } from '../StyledComponents'

const SearchResultsLink = ({
  buttonText = 'Gene Search', openSearchResults, initialSearch, variant, geneIds,
  familyGuids, familyGuid, ...props
}) => <ButtonLink {...props} content={buttonText} onClick={openSearchResults} />

SearchResultsLink.propTypes = {
  buttonText: PropTypes.string,
  initialSearch: PropTypes.object,
  geneIds: PropTypes.string,
  variant: PropTypes.object,
  familyGuid: PropTypes.string,
  familyGuids: PropTypes.arrayOf(PropTypes.string),
  openSearchResults: PropTypes.func,
}

const mapVariantSearchDispatchToProps = (dispatch, ownProps) => ({
  openSearchResults: () => {
    const { variantId, svType, genomeVersion, chrom, pos, end, endChrom } = ownProps.variant
    const search = {
      // TODO genomeVersion no longer works, add explicit endpoint/ different query body?
      locus: { genomeVersion },
    }
    if (svType) {
      search.locus.rawItems = (endChrom && endChrom !== chrom) ? `${chrom}:${pos - 50}-${pos + 50}` :
        `${chrom}:${pos}-${end}%20`
      search.annotations = { [VEP_GROUP_SV]: [svType, `gCNV_${svType}`] }
    } else {
      search.locus.rawVariantItems = variantId
    }
    dispatch(navigateSavedHashedSearch(
      // TODO allProjectFamilies needs to be genome specific, add explicit endpoint/ different query body?
      { allProjectFamilies: true, search },
      resultsLink => window.open(resultsLink, '_blank'),
    ))
  },
})

export const SeqrVariantSearchLink = connect(null, mapVariantSearchDispatchToProps)(SearchResultsLink)

const INITIAL_GENE_SEARCH = {
  inheritance: { mode: ANY_AFFECTED },
  freqs: FREQUENCIES.filter(({ name }) => name !== THIS_CALLSET_FREQUENCY && name !== SV_CALLSET_FREQUENCY).reduce(
    (acc, { name }) => ({ ...acc, [name]: { af: 0.1 } }), {},
  ),
}

const mapGeneSearchDispatchToProps = (dispatch, ownProps) => ({
  openSearchResults: () => {
    dispatch(navigateSavedHashedSearch(
      {
        projectFamilies: [{ familyGuids: ownProps.familyGuid ? [ownProps.familyGuid] : ownProps.familyGuids }],
        search: {
          ...(ownProps.initialSearch || INITIAL_GENE_SEARCH),
          locus: {
            rawItems: ownProps.geneIds,
          },
        },
      },
      resultsLink => window.open(resultsLink, '_blank'),
    ))
  },
})

export const GeneSearchLink = connect(null, mapGeneSearchDispatchToProps)(SearchResultsLink)

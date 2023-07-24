import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { navigateSavedHashedSearch } from 'redux/rootReducer'
import { VEP_GROUP_SV, ANY_AFFECTED } from 'shared/utils/constants'
import { FREQUENCIES, THIS_CALLSET_FREQUENCY, SV_CALLSET_FREQUENCY } from '../panel/search/constants'
import { ButtonLink } from '../StyledComponents'

const SearchResultsLink = ({
  buttonText = 'Gene Search', openSearchResults, initialSearch, variantId, location, genomeVersion, svType,
  familyGuids, familyGuid, ...props
}) => <ButtonLink {...props} content={buttonText} onClick={openSearchResults} />

SearchResultsLink.propTypes = {
  buttonText: PropTypes.string,
  initialSearch: PropTypes.object,
  location: PropTypes.string,
  variantId: PropTypes.string,
  genomeVersion: PropTypes.string,
  svType: PropTypes.string,
  familyGuid: PropTypes.string,
  familyGuids: PropTypes.arrayOf(PropTypes.string),
  openSearchResults: PropTypes.func,
}

const mapDispatchToProps = (dispatch, ownProps) => ({
  openSearchResults: () => {
    const search = {
      ...(ownProps.initialSearch || {}),
      locus: {
        rawItems: ownProps.location, rawVariantItems: ownProps.variantId,
      },
    }
    if (ownProps.svType) {
      search.annotations = { [VEP_GROUP_SV]: [ownProps.svType, `gCNV_${ownProps.svType}`] }
    }
    const familyGuids = ownProps.familyGuid ? [ownProps.familyGuid] : ownProps.familyGuids
    const projectFamilies = familyGuids && [{ familyGuids }]
    dispatch(navigateSavedHashedSearch(
      { allGenomeProjectFamilies: !projectFamilies && ownProps.genomeVersion, projectFamilies, search },
      resultsLink => window.open(resultsLink, '_blank'),
    ))
  },
})

const ConnectedSearchResultsLink = connect(null, mapDispatchToProps)(SearchResultsLink)

export default ConnectedSearchResultsLink

const getGeneSearchProps = (af, af2) => ({
  inheritance: { mode: ANY_AFFECTED, filter: {} },
  freqs: {
    ...FREQUENCIES.filter(({ name }) => name !== THIS_CALLSET_FREQUENCY && name !== SV_CALLSET_FREQUENCY).reduce(
      (acc, { name }) => ({ ...acc, [name]: { af } }), {},
    ),
    ...FREQUENCIES.filter(({ name }) => name.startsWith('gnomad_') || name === THIS_CALLSET_FREQUENCY).reduce(
      (acc, { name }) => ({ ...acc, [name]: { af: af2 } }), {},
    ),
  },
  qualityFilter: { min_gq: 40, min_ab: 10 },
})

const INITIAL_GENE_SEARCH = getGeneSearchProps(0.1, 0.03)
const RARE_GENE_SEARCH = getGeneSearchProps(0.01, 0.03)

export const GeneSearchLink = props => <ConnectedSearchResultsLink initialSearch={INITIAL_GENE_SEARCH} {...props} />
export const RareGeneSearchLink = props => <ConnectedSearchResultsLink initialSearch={RARE_GENE_SEARCH} {...props} />

import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { navigateSavedHashedSearch } from 'redux/rootReducer'
import { VEP_GROUP_SV, ANY_AFFECTED, FREQUENCIES, TOPMED_FREQUENCY, THIS_CALLSET_FREQUENCY } from 'shared/utils/constants'
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
    ))
  },
})

const ConnectedSearchResultsLink = connect(null, mapDispatchToProps)(SearchResultsLink)

export default ConnectedSearchResultsLink

const INITIAL_GENE_SEARCH = {
  inheritance: { mode: ANY_AFFECTED, filter: {} },
  freqs: {
    ...FREQUENCIES.filter(({ name }) => name !== TOPMED_FREQUENCY).reduce(
      (acc, { name }) => ({ ...acc, [name]: { af: 0.03 } }), {},
    ),
    [THIS_CALLSET_FREQUENCY]: { ac: 3000 }, // TODO use migrated value for 0.03 cutoff
  },
  qualityFilter: { min_gq: 40, min_ab: 10 },
}

export const GeneSearchLink = props => <ConnectedSearchResultsLink initialSearch={INITIAL_GENE_SEARCH} {...props} />

const PERMISSIVE_INITIAL_GENE_SEARCH = {
  ...INITIAL_GENE_SEARCH,
  qualityFilter: { ...INITIAL_GENE_SEARCH.qualityFilter, min_gq: 20 },
}

export const PermissiveGeneSearchLink = props => (
  <ConnectedSearchResultsLink initialSearch={PERMISSIVE_INITIAL_GENE_SEARCH} {...props} />
)

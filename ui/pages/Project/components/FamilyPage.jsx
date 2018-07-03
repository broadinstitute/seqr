import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getFamiliesByGuid, getIndividualsByGuid } from 'redux/selectors'
import { FAMILY_DETAIL_FIELDS } from 'shared/utils/constants'
import Family from 'shared/components/panel/family'
import IndividualRow from './FamilyTable/IndividualRow'

export const FamilyDetail = ({ family, individuals, editCaseReview, ...props }) =>
  <div>
    <Family
      family={family}
      {...props}
    />
    {individuals && individuals.map(individual => (
      <IndividualRow
        key={individual.individualGuid}
        family={family}
        individual={individual}
        editCaseReview={editCaseReview}
      />),
    )}
  </div>

FamilyDetail.propTypes = {
  family: PropTypes.object.isRequired,
  editCaseReview: PropTypes.bool,
  individuals: PropTypes.array,
}

const FamilyPage = ({ family, individualsByGuid }) =>
  <FamilyDetail
    family={family}
    showSearchLinks
    showVariantTags
    showDetails
    individuals={family.individualGuids.map(individualGuid => individualsByGuid[individualGuid])}
    fields={FAMILY_DETAIL_FIELDS}
  />

FamilyPage.propTypes = {
  family: PropTypes.object,
  individualsByGuid: PropTypes.object,
}

const mapStateToProps = (state, ownProps) => ({
  family: getFamiliesByGuid(state)[ownProps.match.params.familyGuid],
  individualsByGuid: getIndividualsByGuid(state),
})

export default connect(mapStateToProps)(FamilyPage)

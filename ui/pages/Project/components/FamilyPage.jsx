import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getFamiliesByGuid } from 'redux/selectors'
import { FAMILY_DETAIL_FIELDS } from 'shared/utils/constants'
import Family from 'shared/components/panel/family'
import IndividualRow from './FamilyTable/IndividualRow'
import { getSortedIndividualsByFamily } from '../selectors'

export const BaseFamilyDetail = ({ family, individuals, editCaseReview, ...props }) =>
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

BaseFamilyDetail.propTypes = {
  family: PropTypes.object.isRequired,
  editCaseReview: PropTypes.bool,
  individuals: PropTypes.array,
}

const mapStateToProps = (state, ownProps) => ({
  family: getFamiliesByGuid(state)[ownProps.familyGuid],
  individuals: ownProps.showIndividuals ? getSortedIndividualsByFamily(state)[ownProps.familyGuid] : null,
})

export const FamilyDetail = connect(mapStateToProps)(BaseFamilyDetail)

const FamilyPage = ({ match }) =>
  <FamilyDetail
    familyGuid={match.params.familyGuid}
    showVariantDetails
    showDetails
    showIndividuals
    fields={FAMILY_DETAIL_FIELDS}
  />

FamilyPage.propTypes = {
  match: PropTypes.object,
}

export default FamilyPage

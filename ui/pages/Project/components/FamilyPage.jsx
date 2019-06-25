import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getFamiliesByGuid, getSortedIndividualsByFamily } from 'redux/selectors'
import { FAMILY_DETAIL_FIELDS } from 'shared/utils/constants'
import ShowReadsButton from 'shared/components/buttons/ShowReadsButton'
import Family from 'shared/components/panel/family'
import FamilyVariantReads from 'shared/components/panel/variants/FamilyVariantReads'
import IndividualRow from './FamilyTable/IndividualRow'

const BaseFamilyDetail = ({ family, individuals, editCaseReview, compact, ...props }) =>
  <div>
    <Family
      family={family}
      compact={compact}
      {...props}
    />
    {!compact && <ShowReadsButton familyGuid={family.familyGuid} igvId={family.familyGuid} padding="0.5em 0 1.5em 0" />}
    <FamilyVariantReads igvId={family.familyGuid} />
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
  compact: PropTypes.bool,
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

import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getFamiliesByGuid, getSortedIndividualsByFamily } from 'redux/selectors'
import { FAMILY_DETAIL_FIELDS } from 'shared/utils/constants'
import Family from 'shared/components/panel/family'
import FamilyVariantReads from 'shared/components/panel/variants/FamilyVariantReads'
import IndividualRow from './FamilyTable/IndividualRow'

const READ_BUTTON_PROPS = { padding: '0.5em 0 1.5em 0' }

const BaseFamilyDetail = React.memo(({ family, individuals, compact, tableName, ...props }) =>
  <div>
    <Family
      family={family}
      compact={compact}
      {...props}
    />
    {!compact && <FamilyVariantReads
      layout={({ reads, showReads }) =>
        <div>
          {showReads}
          {reads}
        </div>}
      familyGuid={family.familyGuid}
      buttonProps={READ_BUTTON_PROPS}
    />}
    {individuals && individuals.map(individual => (
      <IndividualRow
        key={individual.individualGuid}
        family={family}
        individual={individual}
        tableName={tableName}
      />),
    )}
  </div>,
)

BaseFamilyDetail.propTypes = {
  family: PropTypes.object.isRequired,
  individuals: PropTypes.array,
  compact: PropTypes.bool,
  tableName: PropTypes.string,
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

import React from 'react'
import PropTypes from 'prop-types'
import sortBy from 'lodash/sortBy'
import styled from 'styled-components'
import { connect } from 'react-redux'

import {
  getProjectAnalysisGroupFamiliesByGuid,
  getProjectAnalysisGroupIndividualsByGuid,
} from '../selectors'

const DetailContent = styled.div`
 padding: 5px 0px 0px 20px;
`

const FAMILY_SIZE_LABELS = {
  0: plural => ` ${plural ? 'families' : 'family'} with no individuals`,
  1: plural => ` ${plural ? 'families' : 'family'} with 1 individual`,
  2: plural => ` ${plural ? 'families' : 'family'} with 2 individuals`,
  3: plural => ` trio${plural ? 's' : ''}`,
  4: plural => ` quad${plural ? 's' : ''}`,
  5: plural => ` ${plural ? 'families' : 'family'} with 5+ individuals`,
}


const ProjectOverview = ({ familiesByGuid, individualsByGuid }) => {
  const familySizeHistogram = Object.values(familiesByGuid)
    .map(family => Math.min(family.individualGuids.length, 5))
    .reduce((acc, familySize) => (
      { ...acc, [familySize]: (acc[familySize] || 0) + 1 }
    ), {})

  return (
    <div>
      {Object.keys(familiesByGuid).length} Families, {Object.keys(individualsByGuid).length} Individuals
      <DetailContent>
        {
          sortBy(Object.keys(familySizeHistogram)).map(size =>
            <div key={size}>
              {familySizeHistogram[size]} {FAMILY_SIZE_LABELS[size](familySizeHistogram[size] > 1)}
            </div>)
        }
      </DetailContent>
    </div>
  )
}


ProjectOverview.propTypes = {
  familiesByGuid: PropTypes.object.isRequired,
  individualsByGuid: PropTypes.object.isRequired,
}

const mapStateToProps = (state, ownProps) => ({
  familiesByGuid: getProjectAnalysisGroupFamiliesByGuid(state, ownProps),
  individualsByGuid: getProjectAnalysisGroupIndividualsByGuid(state, ownProps),
})

export default connect(mapStateToProps)(ProjectOverview)

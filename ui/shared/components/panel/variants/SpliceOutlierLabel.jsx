import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getSortedIndividualsByFamily, getRnaSeqSignificantJunctionData } from 'redux/selectors'
import { RNASEQ_JUNCTION_PADDING } from 'shared/utils/constants'
import RnaSeqJunctionOutliersTable from 'shared/components/table/RnaSeqJunctionOutliersTable'
import { GeneLabel } from './VariantGene'

const HOVER_DATA_TABLE_PROPS = { basic: 'very', compact: 'very', singleLine: true }

const BaseSpliceOutlierLabels = React.memo((
  { variant, updateReads, significantJunctionOutliers, individualsByFamilyGuid },
) => {
  const { pos, end, familyGuids } = variant
  const individualGuids = familyGuids.reduce((acc, fGuid) => (
    [...acc, ...individualsByFamilyGuid[fGuid].map(individual => individual.individualGuid)]
  ), [])

  const overlappedOutliers = individualGuids.reduce((acc, iGuid) => (
    [...acc, ...(significantJunctionOutliers[iGuid] || [])]
  ), []).filter((outlier) => {
    if ((pos >= outlier.start - RNASEQ_JUNCTION_PADDING) && (pos <= outlier.end + RNASEQ_JUNCTION_PADDING)) {
      return true
    }
    if (end && !variant.endChrom) {
      return (end >= outlier.start - RNASEQ_JUNCTION_PADDING) && (end <= outlier.end + RNASEQ_JUNCTION_PADDING)
    }
    return false
  })

  if (overlappedOutliers.length < 1) {
    return null
  }

  const details = (
    <RnaSeqJunctionOutliersTable
      {...HOVER_DATA_TABLE_PROPS}
      data={overlappedOutliers}
      updateReads={updateReads}
    />
  )
  return (
    <GeneLabel popupHeader="The variant is within these outliers" popupContent={details} color="teal" label="RNA splice" />
  )
})

BaseSpliceOutlierLabels.propTypes = {
  significantJunctionOutliers: PropTypes.object,
  individualsByFamilyGuid: PropTypes.object,
  variant: PropTypes.object,
  updateReads: PropTypes.func,
}

const mapLocusListStateToProps = state => ({
  significantJunctionOutliers: getRnaSeqSignificantJunctionData(state),
  individualsByFamilyGuid: getSortedIndividualsByFamily(state),
})

export default connect(mapLocusListStateToProps)(BaseSpliceOutlierLabels)

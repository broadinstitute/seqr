import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Label, Popup } from 'semantic-ui-react'

import { getSpliceOutliersByChromFamily } from 'redux/selectors'
import { RNASEQ_JUNCTION_PADDING } from 'shared/utils/constants'
import RnaSeqJunctionOutliersTable from 'shared/components/table/RnaSeqJunctionOutliersTable'
import { variantIntervalOverlap } from './VariantUtils'

const HOVER_DATA_TABLE_PROPS = { basic: 'very', compact: 'very', singleLine: true }

const BaseSpliceOutlierLabel = React.memo(({ variant, spliceOutliersByFamily }) => {
  const { pos, end, familyGuids, endChrom } = variant
  const outliers = familyGuids.reduce((acc, fGuid) => (
    [...acc, ...(spliceOutliersByFamily[fGuid] || [])]
  ), [])

  const overlappedOutliers = outliers.filter(variantIntervalOverlap({ pos, end, endChrom }, RNASEQ_JUNCTION_PADDING))

  if (overlappedOutliers.length < 1) {
    return null
  }

  const content = (
    <Label size="mini" content={<span>RNA splice</span>} color="pink" />
  )
  const details = (
    <RnaSeqJunctionOutliersTable
      {...HOVER_DATA_TABLE_PROPS}
      data={overlappedOutliers}
      showPopupColumns
    />
  )
  return (
    <Popup trigger={content} content={details} size="tiny" wide hoverable />
  )
})

BaseSpliceOutlierLabel.propTypes = {
  spliceOutliersByFamily: PropTypes.object,
  variant: PropTypes.object,
}

const mapLocusListStateToProps = (state, ownProps) => ({
  spliceOutliersByFamily: getSpliceOutliersByChromFamily(state)[ownProps.variant.chrom],
})

export default connect(mapLocusListStateToProps)(BaseSpliceOutlierLabel)

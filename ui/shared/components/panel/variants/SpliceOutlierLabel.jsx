import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import DataTable from 'shared/components/table/DataTable'
import { RNASEQ_JUNCTION_PADDING, RNA_SEQ_SPLICE_COLUMNS } from 'shared/utils/constants'
import { getLocus } from 'shared/components/panel/variants/VariantUtils'
import { COVERAGE_TYPE, JUNCTION_TYPE } from 'shared/components/panel/family/constants'
import { getIndividualGeneDataByFamilyGene } from './selectors'
import { GeneLabel } from './VariantGene'

const HOVER_DATA_TABLE_PROPS = { basic: 'very', compact: 'very', singleLine: true }

const INDIVIDUAL_NAME_COLUMN = { name: 'individualName', content: '', format: ({ individualName }) => (<b>{individualName}</b>) }

const RNA_SEQ_SPLICE_TAB_COLUMNS = [
  INDIVIDUAL_NAME_COLUMN,
  ...RNA_SEQ_SPLICE_COLUMNS,
]

const handleClick = (intersectedOutliers, updateReads, familyGuid) => (rowId) => {
  const row = intersectedOutliers.find(r => r.idField === rowId)
  const { chrom, start, end, tissueType } = row
  updateReads(familyGuid, getLocus(chrom, start, RNASEQ_JUNCTION_PADDING, end - start),
    [JUNCTION_TYPE, COVERAGE_TYPE], tissueType)
}

const BaseSpliceOutlierLabels = React.memo(({ individualGeneData, variant, updateReads }) => {
  const { pos, end } = variant
  const outliers = Object.values(individualGeneData?.rnaSeqSplData || {}).flat()

  if (outliers.length < 1) {
    return null
  }

  const intersectedOutliers = outliers.filter((outlier) => {
    if ((pos >= outlier.start - RNASEQ_JUNCTION_PADDING) && (pos <= outlier.end + RNASEQ_JUNCTION_PADDING)) {
      return true
    }
    if (end && !variant.endChrom) {
      return (end >= outlier.start - RNASEQ_JUNCTION_PADDING) && (end <= outlier.end + RNASEQ_JUNCTION_PADDING)
    }
    return false
  })

  if (intersectedOutliers.length < 1) {
    return null
  }

  const details = (
    <DataTable
      {...HOVER_DATA_TABLE_PROPS}
      data={intersectedOutliers}
      idField="idField"
      columns={RNA_SEQ_SPLICE_TAB_COLUMNS}
      onClickRow={handleClick(intersectedOutliers, updateReads, variant.familyGuids[0])}
    />
  )
  return (
    <GeneLabel popupHeader="The variant is within these outliers" popupContent={details} color="teal" label="RNA splice" />
  )
})

BaseSpliceOutlierLabels.propTypes = {
  individualGeneData: PropTypes.object,
  variant: PropTypes.object,
  updateReads: PropTypes.func,
}

const mapLocusListStateToProps = (state, ownProps) => ({
  individualGeneData: getIndividualGeneDataByFamilyGene(state)[ownProps.variant.familyGuids[0]],
})

export default connect(mapLocusListStateToProps)(BaseSpliceOutlierLabels)

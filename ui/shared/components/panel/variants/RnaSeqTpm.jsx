import React from 'react'
import PropTypes from 'prop-types'
import Boxplot from 'gtex-d3/src/modules/Boxplot'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { TISSUE_DISPLAY } from 'shared/utils/constants'
import GtexLauncher from '../../graph/GtexLauncher'
import 'gtex-d3/css/boxplot.css'

const GTEX_TISSUES = {
  WB: 'Whole_Blood',
  F: 'Cells_Cultured_fibroblasts',
  M: 'Muscle_Skeletal',
  L: 'Cells_EBV-transformed_lymphocytes',
}

const GTEX_TISSUE_LOOKUP = Object.entries(GTEX_TISSUES).reduce((acc, [k, v]) => ({ ...acc, [v]: k }), {})

const PLOT_WIDTH = 600
const PLOT_MARGIN_LEFT = 40
const PLOT_OPTIONS = {
  width: PLOT_WIDTH,
  height: 450,
  padding: 0.35,
  marginLeft: PLOT_MARGIN_LEFT,
  marginTop: 0,
  marginBottom: 100,
  xAxisFontSize: 12,
  yAxisLabelFontSize: 14,
  yAxisUnit: 'TPM',
}

const loadFamilyRnaSeq = (geneId, familyGuid) => onSuccess => (
  new HttpRequestHelper(`/api/family/${familyGuid}/rna_seq_data/${geneId}`, onSuccess, () => {}).get()
)

const parseGtexTissue = familyExpressionData => ({
  tissueSiteDetailId: Object.keys(familyExpressionData).map(tissue => GTEX_TISSUES[tissue]),
})

const renderGtex = (gtexExpressionData, familyExpressionData, containerElement) => {
  const boxplotData = Object.entries(familyExpressionData).reduce((acc, [tissue, { rdgData, individualData }]) => ([
    ...acc,
    { label: `*RDG - ${TISSUE_DISPLAY[tissue]}`, color: 'efefef', data: rdgData },
    ...Object.entries(individualData).map(([individual, tpm]) => ({ label: individual, data: [tpm] })),
  ]), [])

  const tissues = Object.keys(familyExpressionData)
  const numEntries = (tissues.length * 2) + boxplotData.length
  const marginRight = PLOT_WIDTH - PLOT_MARGIN_LEFT - (numEntries * 80)
  // TODO clean up
  boxplotData.push(...gtexExpressionData.data.map(({ data, tissueSiteDetailId }) => (
    { data, label: `*GTEx - ${TISSUE_DISPLAY[GTEX_TISSUE_LOOKUP[tissueSiteDetailId]]}`, color: 'efefef' }
  )))
  const boxplot = new Boxplot(boxplotData, false)
  boxplot.render(containerElement, { ...PLOT_OPTIONS, marginRight })
}

const RnaSeqTpm = ({ geneId, familyGuid }) => (
  <GtexLauncher
    geneId={geneId}
    renderGtex={renderGtex}
    fetchAdditionalData={loadFamilyRnaSeq(geneId, familyGuid)}
    getAdditionalExpressionParams={parseGtexTissue}
  />
)

RnaSeqTpm.propTypes = {
  geneId: PropTypes.string.isRequired,
  familyGuid: PropTypes.string.isRequired,
}

export default RnaSeqTpm

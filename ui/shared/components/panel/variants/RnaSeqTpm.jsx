import React from 'react'
import PropTypes from 'prop-types'
import Boxplot from 'gtex-d3/src/modules/Boxplot'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { TISSUE_DISPLAY } from 'shared/utils/constants'
import GtexLauncher, { GTEX_HOST } from '../../graph/GtexLauncher'
import 'gtex-d3/css/boxplot.css'

const GTEX_CONTAINER_ID = 'gene-tissue-tpm-plot'

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

const launchGtex = (geneId, familyGuid) => (gencodeId) => {
  new HttpRequestHelper(`/api/family/${familyGuid}/rna_seq_data/${geneId}`,
    (responseJson) => {
      const boxplotData = Object.entries(responseJson).reduce((acc, [tissue, { rdgData, individualData }]) => ([
        ...acc,
        { label: `*RDG - ${TISSUE_DISPLAY[tissue]}`, color: 'efefef', data: rdgData },
        ...Object.entries(individualData).map(([individual, tpm]) => ({ label: individual, data: [tpm] })),
      ]), [])

      const tissues = Object.keys(responseJson)
      const gtexTissuesId = tissues.map(tissue => GTEX_TISSUES[tissue]).join(',')
      const numEntries = (tissues.length * 2) + boxplotData.length
      const marginRight = PLOT_WIDTH - PLOT_MARGIN_LEFT - (numEntries * 80)

      new HttpRequestHelper(`${GTEX_HOST}expression/geneExpression`,
        (gtexJson) => {
          boxplotData.push(...gtexJson.geneExpression.map(({ data, tissueSiteDetailId }) => (
            { data, label: `*GTEx - ${TISSUE_DISPLAY[GTEX_TISSUE_LOOKUP[tissueSiteDetailId]]}`, color: 'efefef' }
          )))
        },
        () => {}).get({ tissueSiteDetailId: gtexTissuesId, gencodeId }).then(() => {
        const boxplot = new Boxplot(boxplotData, false)
        boxplot.render(GTEX_CONTAINER_ID, { ...PLOT_OPTIONS, marginRight })
      })
    }, () => {}).get()
}

const RnaSeqTpm = ({ geneId, familyGuid }) => (
  <GtexLauncher geneId={geneId} containerId={GTEX_CONTAINER_ID} launchGtex={launchGtex(geneId, familyGuid)} />
)

RnaSeqTpm.propTypes = {
  geneId: PropTypes.string.isRequired,
  familyGuid: PropTypes.string.isRequired,
}

export default RnaSeqTpm

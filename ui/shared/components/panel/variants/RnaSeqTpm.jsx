import React from 'react'
import PropTypes from 'prop-types'
import Boxplot from 'gtex-d3/src/modules/Boxplot'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
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

const TISSUE_DISPLAY = {
  WB: 'Whole Blood',
  F: 'Fibroblast',
  M: 'Muscle',
  L: 'Lymphocyte',
}

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

const launchGtex = tpms => (geneId) => {
  const tissues = [...new Set(Object.values(tpms).map(({ sampleTissueType }) => sampleTissueType))]
  const sampleData = Object.entries(tpms).map(([individual, { tpm }]) => ({ label: individual, data: [tpm] }))
  // TODO fetch RDG data
  new HttpRequestHelper(`${GTEX_HOST}expression/geneExpression`,
    (responseJson) => {
      const boxplotData = [
        ...responseJson.geneExpression.map(({ data, tissueSiteDetailId }) => (
          { data, label: `*GTEx - ${TISSUE_DISPLAY[GTEX_TISSUE_LOOKUP[tissueSiteDetailId]]}`, color: 'efefef' }
        )),
        ...sampleData,
      ]

      const numEntries = tissues.length + sampleData.length
      const marginRight = PLOT_WIDTH - PLOT_MARGIN_LEFT - (numEntries * 80)

      const boxplot = new Boxplot(boxplotData, false)
      boxplot.render(GTEX_CONTAINER_ID, { ...PLOT_OPTIONS, marginRight })
    }).get({ tissueSiteDetailId: tissues.map(tissue => GTEX_TISSUES[tissue]).join(','), gencodeId: geneId })
}

const RnaSeqTpm = ({ geneId, tpms }) => (
  <GtexLauncher geneId={geneId} containerId={GTEX_CONTAINER_ID} launchGtex={launchGtex(tpms)} />
)

RnaSeqTpm.propTypes = {
  geneId: PropTypes.string.isRequired,
  tpms: PropTypes.object,
}

export default RnaSeqTpm

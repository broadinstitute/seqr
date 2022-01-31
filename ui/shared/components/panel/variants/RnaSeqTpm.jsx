import React from 'react'
import PropTypes from 'prop-types'
import Boxplot from 'gtex-d3/src/modules/Boxplot'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { snakecaseToTitlecase } from 'shared/utils/stringUtils'
import GtexLauncher, { GTEX_HOST } from '../../graph/GtexLauncher'

const TISSUE = 'Thyroid,Whole_Blood' // TODO should be a prop
// const TISSUE = 'Thyroid'

const GTEX_CONTAINER_ID = 'gene-tissue-tpm-plot'

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

const launchGtex = (geneId) => {
  new HttpRequestHelper(`${GTEX_HOST}expression/geneExpression`,
    (responseJson) => {
      const boxplotData = [
        ...responseJson.geneExpression.map(({ data, tissueSiteDetailId }) => (
          { data, label: `GTEx - ${snakecaseToTitlecase(tissueSiteDetailId)}`, color: 'efefef' }
        )),
        ...responseJson.geneExpression.map(({ data, tissueSiteDetailId }) => (
          { data, label: tissueSiteDetailId, color: 'efefef' }
        )),
      ]

      const numTissues = TISSUE.split(',').length * 2
      const marginRight = PLOT_WIDTH - PLOT_MARGIN_LEFT - (numTissues * 70)

      const boxplot = new Boxplot(boxplotData, false)
      boxplot.render(GTEX_CONTAINER_ID, { ...PLOT_OPTIONS, marginRight })
    }).get({ tissueSiteDetailId: TISSUE, gencodeId: geneId })
}

const RnaSeqTpm = ({ geneId }) => (
  <GtexLauncher geneId={geneId} containerId={GTEX_CONTAINER_ID} launchGtex={launchGtex} />
)

RnaSeqTpm.propTypes = {
  geneId: PropTypes.string.isRequired,
}

export default RnaSeqTpm

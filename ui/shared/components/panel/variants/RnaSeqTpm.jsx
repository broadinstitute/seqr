import React from 'react'
import PropTypes from 'prop-types'
import Boxplot from 'gtex-d3/src/modules/Boxplot'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { snakecaseToTitlecase } from 'shared/utils/stringUtils'
import GtexLauncher, { GTEX_HOST } from '../../graph/GtexLauncher'

const TISSUE = 'Thyroid,Whole_Blood' // TODO should be a prop

const GTEX_CONTAINER_ID = 'gene-tissue-tpm-plot'

const PLOT_OPTIONS = {
  width: 300,
  height: 450,
  padding: 0.35,
  marginLeft: 40,
  marginRight: 100,
  marginTop: 0,
  marginBottom: 100,
  xAxisFontSize: 12,
  yAxisLabelFontSize: 14,
  yAxisUnit: 'TPM',
}

const launchGtex = (geneId) => {
  new HttpRequestHelper(`${GTEX_HOST}expression/geneExpression`,
    (responseJson) => {
      const boxplot = new Boxplot(responseJson.geneExpression.map(({ data, tissueSiteDetailId }) => (
        { data, label: `GTEx - ${snakecaseToTitlecase(tissueSiteDetailId)}`, color: 'efefef' }
      )), false)
      boxplot.render(GTEX_CONTAINER_ID, PLOT_OPTIONS)
    }).get({ tissueSiteDetailId: TISSUE, gencodeId: geneId })
}

const RnaSeqTpm = ({ geneId }) => (
  <GtexLauncher geneId={geneId} containerId={GTEX_CONTAINER_ID} launchGtex={launchGtex} />
)

RnaSeqTpm.propTypes = {
  geneId: PropTypes.string.isRequired,
}

export default RnaSeqTpm

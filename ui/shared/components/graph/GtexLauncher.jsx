import React from 'react'
import PropTypes from 'prop-types'
import { Segment } from 'semantic-ui-react'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { select } from 'd3-selection'

const CONTAINER_ID = 'gtex-container'
const GTEX_HOST = 'https://gtexportal.org/api/v2/'

export const queryGtex = (path, params, onSuccess, onError) => new HttpRequestHelper(
  `${GTEX_HOST}${path}`, onSuccess, onError,
).get(params, { credentials: 'omit' })

class GtexLauncher extends React.PureComponent {

  static propTypes = {
    geneId: PropTypes.string.isRequired,
    renderGtex: PropTypes.func.isRequired,
    fetchAdditionalData: PropTypes.func.isRequired,
    getAdditionalExpressionParams: PropTypes.func,
    renderOnError: PropTypes.bool,
  }

  componentDidMount() {
    const { geneId, fetchAdditionalData } = this.props
    fetchAdditionalData(additionalData => queryGtex('reference/gene', { geneId },
      (responseJson) => {
        this.loadGeneExpression(responseJson.data[0].gencodeId, additionalData)
      },
      () => {
        this.loadGeneExpression(geneId, additionalData)
      }))
  }

  loadGeneExpression = (gencodeId, additionalData) => {
    const { renderGtex, getAdditionalExpressionParams, renderOnError } = this.props
    const params = getAdditionalExpressionParams ? getAdditionalExpressionParams(additionalData) : {}
    queryGtex(
      'expression/geneExpression',
      { gencodeId, ...params },
      expressionData => renderGtex(expressionData, additionalData, select(`#${CONTAINER_ID}`)),
      renderOnError ? () => renderGtex(null, additionalData, select(`#${CONTAINER_ID}`)) : null,
    )
  }

  render() {
    // TODO use data loader? add loading handling?
    return <Segment id={CONTAINER_ID} />
  }

}

export default GtexLauncher

import React from 'react'
import PropTypes from 'prop-types'
import { Segment } from 'semantic-ui-react'
import { select } from 'd3-selection'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import DataLoader from 'shared/components/DataLoader'

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

  state = { loading: false }

  loadGeneExpression = (gencodeId, additionalData) => {
    const { getAdditionalExpressionParams } = this.props
    const params = getAdditionalExpressionParams ? getAdditionalExpressionParams(additionalData) : {}
    const onComplete = this.onExpressionLoadComplete(additionalData)
    queryGtex(
      'expression/geneExpression',
      { gencodeId, ...params },
      onComplete,
      () => onComplete(null),
    )
  }

  onExpressionLoadComplete = additionalData => (expressionData) => {
    const { renderGtex, renderOnError } = this.props
    this.setState({ loading: false })
    if (expressionData || renderOnError) {
      renderGtex(expressionData, additionalData, select(`#${CONTAINER_ID}`))
    }
  }

  load = () => {
    const { geneId, fetchAdditionalData } = this.props
    this.setState({ loading: true })
    fetchAdditionalData(additionalData => queryGtex('reference/gene', { geneId },
      (responseJson) => {
        this.loadGeneExpression(responseJson.data[0].gencodeId, additionalData)
      },
      () => {
        this.loadGeneExpression(geneId, additionalData)
      }))
  }

  render() {
    const { loading } = this.state
    return <DataLoader content loading={loading} load={this.load}><Segment id={CONTAINER_ID} /></DataLoader>
  }

}

export default GtexLauncher

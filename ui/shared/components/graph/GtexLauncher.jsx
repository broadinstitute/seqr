import React from 'react'
import PropTypes from 'prop-types'
import { Segment } from 'semantic-ui-react'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { select } from 'd3-selection'

export const GTEX_HOST = 'https://gtexportal.org/api/v2/'

export const queryGtex = (path, params, onSuccess, onError) => new HttpRequestHelper(
  `${GTEX_HOST}${path}`, onSuccess, onError,
).get(params, { credentials: 'omit' })

class GtexLauncher extends React.PureComponent {

  static propTypes = {
    geneId: PropTypes.string.isRequired,
    renderGtex: PropTypes.func.isRequired,
    fetchAdditionalData: PropTypes.func.isRequired,
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
    const { renderGtex } = this.props
    queryGtex('expression/geneExpression', { gencodeId }, expressionData => renderGtex(expressionData, additionalData, select(this.container)))
  }

  setElement = (element) => {
    this.container = element
  }

  render() {
    // TODO use data loader? add loading handling?
    return <Segment ref={this.setElement} />
  }

}

export default GtexLauncher

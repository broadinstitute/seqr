import React from 'react'
import PropTypes from 'prop-types'
import { Segment } from 'semantic-ui-react'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'

export const GTEX_HOST = 'https://gtexportal.org/rest/v1/'

class GtexLauncher extends React.PureComponent {

  static propTypes = {
    geneId: PropTypes.string.isRequired,
    containerId: PropTypes.string.isRequired,
    launchGtex: PropTypes.func.isRequired,
  }

  componentDidMount() {
    const { geneId, launchGtex } = this.props
    new HttpRequestHelper(`${GTEX_HOST}reference/gene`,
      (responseJson) => {
        launchGtex(responseJson.gene[0].gencodeId)
      },
      () => {
        launchGtex(geneId)
      }).get({ format: 'json', geneId })
  }

  render() {
    const { containerId } = this.props
    return <Segment id={containerId} />
  }

}

export default GtexLauncher

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { launch } from 'gtex-d3/GeneExpressionViolinPlot'

const GtexContainer = styled.div`
`

const GTEX_CONTAINER_ID = 'gene-expression-plot'

class Gtex extends React.PureComponent {

  static propTypes = {
    geneId: PropTypes.string.isRequired,
  }

  render() {
    return <GtexContainer id={GTEX_CONTAINER_ID} />
  }

  componentDidMount() {
    launch(GTEX_CONTAINER_ID, `${GTEX_CONTAINER_ID}-tooltip`, `${this.props.geneId}.5`)
  }
}

export default Gtex

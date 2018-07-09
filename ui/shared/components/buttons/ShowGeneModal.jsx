import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getGenesById } from 'redux/selectors'
import Modal from '../modal/Modal'
import GeneDetail from '../panel/genes/GeneDetail'
import ButtonLink from './ButtonLink'

const ShowGeneModal = ({ gene, geneId, ...linkProps }) =>
  <Modal
    trigger={<ButtonLink {...linkProps}>{gene.symbol}</ButtonLink>}
    title={gene.symbol}
    modalName={`gene-${geneId || gene.geneId}`}
    size="fullscreen"
  >
    <GeneDetail geneId={geneId || gene.geneId} />
  </Modal>

ShowGeneModal.propTypes = {
  gene: PropTypes.object,
  geneId: PropTypes.string,
}

const mapStateToProps = (state, ownProps) => ({
  gene: ownProps.gene || getGenesById(state)[ownProps.geneId],
})

export default connect(mapStateToProps)(ShowGeneModal)

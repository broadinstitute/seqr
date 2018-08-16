import React from 'react'
import PropTypes from 'prop-types'

import Modal from '../modal/Modal'
import GeneDetail from '../panel/genes/GeneDetail'
import ButtonLink from './ButtonLink'

const ShowGeneModal = ({ gene, triggerId, ...linkProps }) =>
  <Modal
    trigger={<ButtonLink {...linkProps}>{gene.symbol}</ButtonLink>}
    title={gene.symbol}
    modalName={`gene-${gene.geneId}-${triggerId}`}
    size="fullscreen"
  >
    <GeneDetail geneId={gene.geneId} />
  </Modal>

ShowGeneModal.propTypes = {
  gene: PropTypes.object,
  triggerId: PropTypes.string,
}

export default ShowGeneModal

import React from 'react'
import PropTypes from 'prop-types'

import Modal from '../modal/Modal'
import GeneDetail from '../panel/genes/GeneDetail'
import ButtonLink from './ButtonLink'

const ShowGeneModal = ({ gene, ...linkProps }) =>
  <Modal
    trigger={<ButtonLink {...linkProps}>{gene.geneSymbol}</ButtonLink>}
    title={gene.geneSymbol}
    modalName={`gene-${gene.geneId}`}
    size="fullscreen"
  >
    <GeneDetail geneId={gene.geneId} />
  </Modal>

ShowGeneModal.propTypes = {
  gene: PropTypes.object,
}

export default ShowGeneModal

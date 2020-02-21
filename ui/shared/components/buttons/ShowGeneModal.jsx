import React from 'react'
import PropTypes from 'prop-types'

import Modal from '../modal/Modal'
import GeneDetail from '../panel/genes/GeneDetail'
import { ButtonLink } from '../StyledComponents'

const ShowGeneModal = ({ gene, modalId = 'gene', ...linkProps }) =>
  <Modal
    trigger={<ButtonLink {...linkProps}>{gene.geneSymbol}</ButtonLink>}
    title={gene.geneSymbol}
    modalName={`${modalId}-${gene.geneId}`}
    size="fullscreen"
  >
    <GeneDetail geneId={gene.geneId} />
  </Modal>

ShowGeneModal.propTypes = {
  gene: PropTypes.object,
  modalId: PropTypes.string,
}

export default ShowGeneModal

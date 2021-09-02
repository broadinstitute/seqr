import React from 'react'
import PropTypes from 'prop-types'

import Modal from '../modal/Modal'
import GeneDetail from '../panel/genes/GeneDetail'
import { ButtonLink } from '../StyledComponents'

// Refactor this into constants.js
// Currently using panelapp colors.
// We should use seqr colors.
const confidenceLevelColors = {
  1: '#d9534f', // red
  2: '#f0ad4e', // amber
  3: '#3fad46', // green
  4: '#3fad46', // green
}

const ShowGeneModal = ({ pagene, gene, modalId = 'gene', ...linkProps }) =>
  <Modal
    trigger={
      <ButtonLink
        background={confidenceLevelColors[pagene.confidenceLevel]}
        {...linkProps}
      >
        {gene.geneSymbol}
      </ButtonLink>}
    title={gene.geneSymbol}
    modalName={`${modalId}-${gene.geneId}`}
    size="fullscreen"
  >
    <GeneDetail geneId={gene.geneId} />
  </Modal>

ShowGeneModal.propTypes = {
  pagene: PropTypes.object,
  gene: PropTypes.object,
  modalId: PropTypes.string,
}

export default ShowGeneModal

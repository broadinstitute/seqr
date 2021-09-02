import React from 'react'
import PropTypes from 'prop-types'

import Modal from '../modal/Modal'
import GeneDetail from '../panel/genes/GeneDetail'
import { ButtonLink } from '../StyledComponents'

// Refactor this into constants.js
// Currently using panelapp colors.
// We should use seqr colors.
const confidenceLevelColors = {
  0: 'none',
  1: '#d9534f66', // red
  2: '#f0ad4e66', // amber
  3: '#3fad4666', // green
  4: '#3fad4666', // green
}

const ShowGeneModal = ({ pagene, gene, modalId = 'gene', ...linkProps }) =>
  <Modal
    trigger={
      <ButtonLink
        padding="0.5em"
        background={confidenceLevelColors[pagene?.confidenceLevel || 0]}
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

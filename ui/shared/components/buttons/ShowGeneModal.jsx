import React from 'react'
import PropTypes from 'prop-types'

import Modal from '../modal/Modal'
import GeneDetail from '../panel/genes/GeneDetail'
import { ButtonLink } from '../StyledComponents'
import { PANEL_APP_CONFIDENCE_LEVEL_COLORS } from '../../utils/constants'

const ShowGeneModal = ({ pagene, gene, modalId = 'gene', ...linkProps }) =>
  <Modal
    trigger={
      <ButtonLink
        padding="0.5em"
        background={PANEL_APP_CONFIDENCE_LEVEL_COLORS[pagene?.confidenceLevel || 0]}
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

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Popup } from 'semantic-ui-react'

import { GENOME_VERSION_37 } from '../../../utils/constants'

const SequenceContainer = styled.span`
  word-break: break-all;
  color: ${props => props.color || 'inherit'};
`

export const TranscriptLink = styled.a.attrs(({ variant, transcript }) => ({
  target: '_blank',
  href: `http://${variant.genomeVersion === GENOME_VERSION_37 ? 'grch37' : 'useast'}.ensembl.org/Homo_sapiens/Transcript/Summary?t=${transcript.transcriptId}`,
  children: transcript.transcriptId,
}))`
  font-size: 1.3em;
  font-weight: normal;
`

export const getLocus = (chrom, pos, rangeSize, endOffset = 0) =>
  `chr${chrom}:${pos - rangeSize}-${pos + endOffset + rangeSize}`

const MAX_SEQUENCE_LENGTH = 30
const SEQUENCE_POPUP_STYLE = { wordBreak: 'break-all' }

export const Sequence = React.memo(({ sequence, ...props }) =>
  <SequenceContainer {...props}>
    {sequence.length > MAX_SEQUENCE_LENGTH ?
      <Popup trigger={<span>{`${sequence.substring(0, MAX_SEQUENCE_LENGTH)}...`}</span>} content={sequence} style={SEQUENCE_POPUP_STYLE} /> :
      sequence
    }
  </SequenceContainer>,
)

Sequence.propTypes = {
  sequence: PropTypes.string.isRequired,
}

const parseHgvs = hgvs => (hgvs || '').split(':').pop()

export const ProteinSequence = React.memo(({ hgvs }) =>
  <Sequence color="black" sequence={parseHgvs(hgvs)} />,
)

ProteinSequence.propTypes = {
  hgvs: PropTypes.string.isRequired,
}

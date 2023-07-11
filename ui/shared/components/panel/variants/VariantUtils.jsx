import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Popup } from 'semantic-ui-react'

import { GENOME_VERSION_37, getVariantMainGeneId, RNASEQ_JUNCTION_PADDING } from '../../../utils/constants'

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

export const has37Coords = ({ genomeVersion, liftedOverGenomeVersion, liftedOverPos }) => (
  genomeVersion === GENOME_VERSION_37 || (liftedOverGenomeVersion === GENOME_VERSION_37 && liftedOverPos))

export const compHetGene = (variants) => {
  const sharedGeneIds = variants.slice(1).reduce(
    (acc, v) => acc.filter(geneId => geneId in (v.transcripts || {})), Object.keys(variants[0].transcripts || {}),
  )
  if (sharedGeneIds.length > 1) {
    const mainSharedGene = variants.map(v => getVariantMainGeneId(v)).find(geneId => sharedGeneIds.includes(geneId))
    if (mainSharedGene) {
      return mainSharedGene
    }
  }
  return sharedGeneIds[0]
}

export const getLocus =
  (chrom, pos, rangeSize, endOffset = 0) => `chr${chrom}:${pos - rangeSize}-${pos + endOffset + rangeSize}`

const MAX_SEQUENCE_LENGTH = 30
const SEQUENCE_POPUP_STYLE = { wordBreak: 'break-all' }

export const Sequence = React.memo(({ sequence, ...props }) => (
  <SequenceContainer {...props}>
    {sequence.length > MAX_SEQUENCE_LENGTH ?
      <Popup trigger={<span>{`${sequence.substring(0, MAX_SEQUENCE_LENGTH)}...`}</span>} content={sequence} style={SEQUENCE_POPUP_STYLE} /> :
      sequence}
  </SequenceContainer>
))

Sequence.propTypes = {
  sequence: PropTypes.string.isRequired,
}

const parseHgvs = hgvs => (hgvs || '').split(':').pop()

export const ProteinSequence = React.memo(({ hgvs }) => <Sequence color="black" sequence={parseHgvs(hgvs)} />)

ProteinSequence.propTypes = {
  hgvs: PropTypes.string.isRequired,
}

const variantIntervalOverlap = (variant, padding) => (interval) => {
  const { pos, end, liftedOverPos, liftedOverGenomeVersion } = variant
  const variantPos = (liftedOverGenomeVersion && liftedOverGenomeVersion === interval.genomeVersion) ?
    liftedOverPos : pos
  if (!variantPos) {
    return false
  }
  if ((variantPos >= interval.start - padding) && (variantPos <= interval.end + padding)) {
    return true
  }
  if (end && !variant.endChrom) {
    const variantPosEnd = variantPos + (end - pos)
    return (variantPosEnd >= interval.start - padding) && (variantPosEnd <= interval.end + padding)
  }
  return false
}

export const getOverlappedIntervals = (variant, intervals, getIntervalGroup, padding = 0) => {
  const { familyGuids = [] } = variant
  return familyGuids.reduce((acc, fGuid) => (
    intervals ? [
      ...acc, ...(intervals[getIntervalGroup(fGuid)] || []).filter(variantIntervalOverlap(variant, padding)),
    ] : []
  ), [])
}

export const getOverlappedSpliceOutliers = (variant, spliceOutliersByFamily) => (
  getOverlappedIntervals(variant, spliceOutliersByFamily, fGuid => fGuid, RNASEQ_JUNCTION_PADDING)
)

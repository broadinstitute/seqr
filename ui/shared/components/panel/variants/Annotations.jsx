import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Popup, Label, Icon } from 'semantic-ui-react'

import { HorizontalSpacer, VerticalSpacer } from '../../Spacers'
import Modal from '../../modal/Modal'
import ButtonLink from '../../buttons/ButtonLink'
import Transcripts from './Transcripts'
import { LocusListLabels } from './VariantGene'


const SequenceContainer = styled.span`
  word-break: break-all;
  color: ${props => props.color || 'inherit'};
`

const LargeText = styled.div`
  font-size: 1.2em;
`

export const getLocus = (variant, rangeSize) =>
  `chr${variant.chrom}:${variant.pos - rangeSize}-${variant.pos + rangeSize}`

const ucscBrowserLink = (variant, genomeVersion) => {
  /* eslint-disable space-infix-ops */
  genomeVersion = genomeVersion || variant.genomeVersion
  genomeVersion = genomeVersion === '37' ? '19' : genomeVersion
  const highlight = `hg${genomeVersion}.chr${variant.chrom}:${variant.pos}-${variant.pos + (variant.ref.length-1)}`
  const position = getLocus(variant, 10)
  return `http://genome.ucsc.edu/cgi-bin/hgTracks?db=hg${genomeVersion}&highlight=${highlight}&position=${position}`
}

const MAX_SEQUENCE_LENGTH = 30
const SEQUENCE_POPUP_STYLE = { wordBreak: 'break-all' }

const Sequence = ({ sequence, ...props }) =>
  <SequenceContainer {...props}>
    {sequence.length > MAX_SEQUENCE_LENGTH ?
      <Popup trigger={<span>{`${sequence.substring(0, MAX_SEQUENCE_LENGTH)}...`}</span>} content={sequence} style={SEQUENCE_POPUP_STYLE} /> :
      sequence
    }
  </SequenceContainer>

Sequence.propTypes = {
  sequence: PropTypes.string.isRequired,
}

export const ProteinSequence = ({ hgvs }) =>
  <Sequence color="black" sequence={hgvs.split(':').pop()} />

ProteinSequence.propTypes = {
  hgvs: PropTypes.string.isRequired,
}

const LOF_FILTER_MAP = {
  END_TRUNC: { title: 'End Truncation', message: 'This variant falls in the last 5% of the transcript' },
  INCOMPLETE_CDS: { title: 'Incomplete CDS', message: 'The start or stop codons are not known for this transcript' },
  EXON_INTRON_UNDEF: { title: 'Exon-Intron Boundaries', message: 'The exon/intron boundaries of this transcript are undefined in the EnsEMBL API' },
  SMALL_INTRON: { title: 'Small Intron', message: 'The LoF falls in a transcript whose exon/intron boundaries are undefined in the EnsEMBL API' },
  NON_CAN_SPLICE: { title: 'Non Canonical Splicing', message: 'This variant falls in a non-canonical splice site (not GT..AG)' },
  NON_CAN_SPLICE_SURR: { title: 'Non Canonical Splicing', message: 'This exon has surrounding splice sites that are non-canonical (not GT..AG)' },
  ANC_ALLELE: { title: 'Ancestral Allele', message: 'The alternate allele reverts the sequence back to the ancestral state' },
}

const annotationVariations = (mainTranscript, variant) => {
  const variations = []
  if (mainTranscript.hgvsc) {
    const hgvsc = mainTranscript.hgvsc.split(':')[1].replace('c.', '')
    variations.push(
      `${mainTranscript.symbol}:c.${hgvsc}`, //TTN:c.78674T>C
      `c.${hgvsc}`, //c.1282C>T
      hgvsc, //1282C>T
      hgvsc.replace('>', '->'), //1282C->T
      hgvsc.replace('>', '-->'), //1282C-->T
      (`c.${hgvsc}`).replace('>', '/'), //c.1282C/T
      hgvsc.replace('>', '/'), //1282C/T
      `${mainTranscript.symbol}:${hgvsc}`, //TTN:78674T>C
    )
  }

  if (mainTranscript.hgvsp) {
    const hgvsp = mainTranscript.hgvsp.split(':')[1].replace('p.', '')
    variations.push(
      `${mainTranscript.symbol}:p.${hgvsp}`, //TTN:p.Ile26225Thr
      `${mainTranscript.symbol}:${hgvsp}`, //TTN:Ile26225Thr
    )
  }

  if (mainTranscript.aminoAcids && mainTranscript.proteinPosition) {
    const aminoAcids = mainTranscript.aminoAcids.split('/')
    const aa1 = aminoAcids[0] || ''
    const aa2 = aminoAcids[1] || ''

    variations.push(
      `${aa1}${mainTranscript.proteinPosition}${aa2}`, //A625V
      `${mainTranscript.proteinPosition}${aa1}/${aa2}`, //625A/V
    )
  }

  if (variant.alt && variant.ref && variant.pos) {
    variations.push(
      `${variant.pos}${variant.ref}->${variant.alt}`, //179432185A->G
      `${variant.pos}${variant.ref}-->${variant.alt}`, //179432185A-->G
      `${variant.pos}${variant.ref}/${variant.alt}`, //179432185A/G
      `${variant.pos}${variant.ref}>${variant.alt}`, //179432185A>G
      `g.${variant.pos}${variant.ref}>${variant.alt}`, //g.179432185A>G
    )
  }

  return variations
}

const Annotations = ({ variant }) => {
  const { vepGroup, rsid } = variant.annotation
  const mainTranscript = variant.annotation.mainTranscript || {}

  const variations = annotationVariations(mainTranscript, variant)
  const lofDetails = (mainTranscript.lof === 'LC' || mainTranscript.lofFlags === 'NAGNAG_SITE') ? [
    ...[...new Set(mainTranscript.lofFilter.split(/&|,/g))].map((lofFilterKey) => {
      const lofFilter = LOF_FILTER_MAP[lofFilterKey] || { message: lofFilterKey }
      return <div key={lofFilterKey}><b>LOFTEE: {lofFilter.title}</b><br />{lofFilter.message}.</div>
    }),
    mainTranscript.lofFlags === 'NAGNAG_SITE' ?
      <div key="NAGNAG_SITE">LOFTEE: <b>NAGNAG site</b>This acceptor site is rescued by another adjacent in-frame acceptor site.</div>
      : null,
  ] : null

  return (
    <div>
      { vepGroup &&
        <Modal
          modalName={`${variant.variantId}-annotations`}
          title="Transcripts"
          size="large"
          trigger={<ButtonLink>{vepGroup.replace(/_/g, ' ')}</ButtonLink>}
        >
          <Transcripts variant={variant} />
        </Modal>
      }
      { lofDetails &&
        <span>
          <HorizontalSpacer width={12} />
          <Popup
            trigger={<Label color="red" horizontal size="tiny">LC LoF</Label>}
            content={lofDetails}
          />
        </span>
      }
      { mainTranscript.hgvsc &&
        <div>
          <b>HGVS.C</b><HorizontalSpacer width={5} /><ProteinSequence hgvs={mainTranscript.hgvsc} />
        </div>
      }
      { mainTranscript.hgvsp &&
        <div>
          <b>HGVS.P</b><HorizontalSpacer width={5} /><ProteinSequence hgvs={mainTranscript.hgvsp} />
        </div>
      }
      { Object.keys(mainTranscript).length > 0 && <VerticalSpacer height={10} />}
      <LargeText>
        <a href={ucscBrowserLink(variant)} target="_blank" rel="noopener noreferrer"><b>{variant.chrom}:{variant.pos}</b></a>
        <HorizontalSpacer width={10} />
        <Sequence sequence={variant.ref} />
        <Icon name="angle right" />
        <Sequence sequence={variant.alt} />
      </LargeText>
      {rsid &&
        <div>
          <a href={`http://www.ncbi.nlm.nih.gov/SNP/snp_ref.cgi?searchType=adhoc_search&type=rs&rs=${rsid}`} target="_blank" rel="noopener noreferrer">
            {rsid}
          </a>
        </div>
      }
      {variant.liftedOverGenomeVersion === '37' && (
        variant.liftedOverPos ?
          <div>
            hg19:<HorizontalSpacer width={5} />
            <a href={ucscBrowserLink(variant, '37')} target="_blank" rel="noopener noreferrer">
              chr{variant.liftedOverChrom}:{variant.liftedOverPos}
            </a>
          </div>
          : <div>hg19: liftover failed</div>
        )
      }
      <VerticalSpacer height={5} />
      <LocusListLabels locusLists={variant.locusLists} />
      <VerticalSpacer height={5} />
      {mainTranscript.symbol &&
        <div>
          <a href={`https://www.google.com/search?q=${mainTranscript.symbol}+${variations.join('+')}`} target="_blank" rel="noopener noreferrer">
            google
          </a>
          <HorizontalSpacer width={5} />|<HorizontalSpacer width={5} />
          <a href={`https://www.ncbi.nlm.nih.gov/pubmed?term=${mainTranscript.symbol} AND ( ${variations.join(' OR ')})`} target="_blank" rel="noopener noreferrer">
            pubmed
          </a>
        </div>
      }
    </div>
  )
}

Annotations.propTypes = {
  variant: PropTypes.object,
}

export default Annotations

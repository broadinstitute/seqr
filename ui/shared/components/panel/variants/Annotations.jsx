import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Popup, Label } from 'semantic-ui-react'

import { HorizontalSpacer } from '../../Spacers'
import Modal from '../../modal/Modal'
import ButtonLink from '../../buttons/ButtonLink'
import Transcripts from './Transcripts'


const ProteinSequenceContainer = styled.span`
  word-break: break-all;
  color: black;
`

export const ProteinSequence = ({ hgvs }) =>
  <ProteinSequenceContainer>{hgvs.split(':').pop()}</ProteinSequenceContainer>

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
  const { mainTranscript, vepGroup } = variant.annotation
  if (!mainTranscript) {
    return null
  }

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
      <div>
        <a target="_blank" href={`https://www.google.com/search?q=${mainTranscript.symbol}+${variations.join('+')}`}>google</a>
        <HorizontalSpacer width={5} />|<HorizontalSpacer width={5} />
        <a target="_blank" href={`https://www.ncbi.nlm.nih.gov/pubmed?term=${mainTranscript.symbol} AND ( ${variations.join(' OR ')})`}>pubmed</a>
      </div>
    </div>
  )
}

Annotations.propTypes = {
  variant: PropTypes.object,
}

export default Annotations

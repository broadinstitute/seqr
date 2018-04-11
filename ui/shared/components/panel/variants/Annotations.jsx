import React from 'react'
import PropTypes from 'prop-types'
import { Popup, Grid, Label } from 'semantic-ui-react'

import { HorizontalSpacer } from '../../Spacers'
import { BreakWord } from './Variants'


const LOF_FILTER_MAP = {
  END_TRUNC: { title: 'End Truncation', message: 'This variant falls in the last 5% of the transcript' },
  INCOMPLETE_CDS: { title: 'Incomplete CDS', message: 'The start or stop codons are not known for this transcript' },
  EXON_INTRON_UNDEF: { title: 'Exon-Intron Boundaries', message: 'The exon/intron boundaries of this transcript are undefined in the EnsEMBL API' },
  SMALL_INTRON: { title: 'Small Intron', message: 'The LoF falls in a transcript whose exon/intron boundaries are undefined in the EnsEMBL API' },
  NON_CAN_SPLICE: { title: 'Non Canonical Splicing', message: 'This variant falls in a non-canonical splice site (not GT..AG)' },
  NON_CAN_SPLICE_SURR: { title: 'Non Canonical Splicing', message: 'This exon has surrounding splice sites that are non-canonical (not GT..AG)' },
  ANC_ALLELE: { title: 'Ancestral BreakWord', message: 'The alternate allele reverts the sequence back to the ancestral state' },
}

const annotationVariations = (worstVepAnnotation, symbol, variant) => {
  const variations = []
  if (worstVepAnnotation.hgvsc) {
    const hgvsc = worstVepAnnotation.hgvsc.split(':')[1].replace('c.', '')
    variations.push(
      `${symbol}:c.${hgvsc}`, //TTN:c.78674T>C
      `c.${hgvsc}`, //c.1282C>T
      hgvsc, //1282C>T
      hgvsc.replace('>', '->'), //1282C->T
      hgvsc.replace('>', '-->'), //1282C-->T
      (`c.${hgvsc}`).replace('>', '/'), //c.1282C/T
      hgvsc.replace('>', '/'), //1282C/T
      `${symbol}:${hgvsc}`, //TTN:78674T>C
    )
  }

  if (worstVepAnnotation.hgvsp) {
    const hgvsp = worstVepAnnotation.hgvsp.split(':')[1].replace('p.', '')
    variations.push(
      `${symbol}:p.${hgvsp}`, //TTN:p.Ile26225Thr
      `${symbol}:${hgvsp}`, //TTN:Ile26225Thr
    )
  }

  if (worstVepAnnotation.amino_acids && worstVepAnnotation.protein_position) {
    const aminoAcids = worstVepAnnotation.amino_acids.split('/')
    const aa1 = aminoAcids[0] || ''
    const aa2 = aminoAcids[1] || ''

    variations.push(
      `${aa1}${worstVepAnnotation.protein_position}${aa2}`, //A625V
      `${worstVepAnnotation.protein_position}${aa1}/${aa2}`, //625A/V
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
  const worstVepAnnotation = variant.annotations.vep_annotation[variant.annotations.worst_vep_annotation_index]
  if (!worstVepAnnotation) {
    return null
  }

  const symbol = worstVepAnnotation.gene_symbol || worstVepAnnotation.symbol
  const variations = annotationVariations(worstVepAnnotation, symbol, variant)

  return (
    <Grid.Column width={4}>
      { variant.annotations.vep_group && // TODO actually do something on click
        <a style={{ fontSize: '14px' }}>{variant.annotations.vep_group.replace(/_/g, ' ')}</a>
      }
      { (worstVepAnnotation.lof === 'LC' || worstVepAnnotation.lof_flags === 'NAGNAG_SITE') &&
        <span>
          <HorizontalSpacer width={12} />
          <Popup
            trigger={<Label color="red" horizontal size="tiny">LC LoF</Label>}
            content={[
              ...[...new Set(worstVepAnnotation.lof_filter.split('&'))].map((lofFilterKey) => {
                const lofFilter = LOF_FILTER_MAP[lofFilterKey]
                return <span key={lofFilterKey}><b>LOFTEE: {lofFilter.title}</b><br />{lofFilter.message}.</span>
              }),
              worstVepAnnotation.lof_flags === 'NAGNAG_SITE' ?
                <span key="NAGNAG_SITE">LOFTEE: <b>NAGNAG site</b><br />This acceptor site is rescued by another adjacent in-frame acceptor site.</span>
                : null,
            ]}
          />
        </span>
      }
      { worstVepAnnotation.hgvsc &&
        <span>
          <br />
          <b>HGVS.C</b><HorizontalSpacer width={5} /><BreakWord>{worstVepAnnotation.hgvsc.split(':').pop()}</BreakWord>
        </span>
      }
      { worstVepAnnotation.hgvsp &&
        <span>
          <br />
          <b>HGVS.P</b><HorizontalSpacer width={5} /><BreakWord>{worstVepAnnotation.hgvsp.split(':').pop()}</BreakWord>
        </span>
      }
      <br />
      <a target="_blank" href={`https://www.google.com/search?q=${symbol}+${variations.join('+')}`}>google</a>
      <HorizontalSpacer width={5} />|<HorizontalSpacer width={5} />
      <a target="_blank" href={`https://www.ncbi.nlm.nih.gov/pubmed?term=${symbol} AND ( ${variations.join(' OR ')})`}>pubmed</a>
    </Grid.Column>
  )
}

Annotations.propTypes = {
  variant: PropTypes.object,
}

export default Annotations

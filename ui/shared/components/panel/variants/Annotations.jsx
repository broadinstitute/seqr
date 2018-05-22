import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Popup, Label, Header, Table, Segment } from 'semantic-ui-react'

import { HorizontalSpacer, VerticalSpacer } from '../../Spacers'
import Modal from '../../modal/Modal'


const ProteinSequenceContainer = styled.span`
  word-break: break-all;
  color: black;
  font-size: ${props => props.size || '1.2em'};
`

const TranscriptLink = styled.a`
  font-size: 1.3em;
  font-weight: ${(props) => { return props.isChosen ? 'bold' : 'normal' }}
`

const AnnotationSection = styled.div`
  display: inline-block;
  padding-right: 30px;
`

const AnnotationLabel = styled.span`
  font-size: .8em;
  font-weight: bolder;
  color: grey;
  padding-right: 10px;
`

const ProtenSequence = ({ hgvs, size }) =>
  <ProteinSequenceContainer size={size}>{hgvs.split(':').pop()}</ProteinSequenceContainer>

ProtenSequence.propTypes = {
  hgvs: PropTypes.string.isRequired,
  size: PropTypes.string,
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

const annotationVariations = (worstVepAnnotation, variant) => {
  const variations = []
  if (worstVepAnnotation.hgvsc) {
    const hgvsc = worstVepAnnotation.hgvsc.split(':')[1].replace('c.', '')
    variations.push(
      `${worstVepAnnotation.symbol}:c.${hgvsc}`, //TTN:c.78674T>C
      `c.${hgvsc}`, //c.1282C>T
      hgvsc, //1282C>T
      hgvsc.replace('>', '->'), //1282C->T
      hgvsc.replace('>', '-->'), //1282C-->T
      (`c.${hgvsc}`).replace('>', '/'), //c.1282C/T
      hgvsc.replace('>', '/'), //1282C/T
      `${worstVepAnnotation.symbol}:${hgvsc}`, //TTN:78674T>C
    )
  }

  if (worstVepAnnotation.hgvsp) {
    const hgvsp = worstVepAnnotation.hgvsp.split(':')[1].replace('p.', '')
    variations.push(
      `${worstVepAnnotation.symbol}:p.${hgvsp}`, //TTN:p.Ile26225Thr
      `${worstVepAnnotation.symbol}:${hgvsp}`, //TTN:Ile26225Thr
    )
  }

  if (worstVepAnnotation.aminoAcids && worstVepAnnotation.proteinPosition) {
    const aminoAcids = worstVepAnnotation.aminoAcids.split('/')
    const aa1 = aminoAcids[0] || ''
    const aa2 = aminoAcids[1] || ''

    variations.push(
      `${aa1}${worstVepAnnotation.proteinPosition}${aa2}`, //A625V
      `${worstVepAnnotation.proteinPosition}${aa1}/${aa2}`, //625A/V
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
  const { worstVepAnnotation, vepAnnotations, vepGroup } = variant.annotation
  if (!worstVepAnnotation) {
    return null
  }

  const variations = annotationVariations(worstVepAnnotation, variant)
  const lofDetails = (worstVepAnnotation.lof === 'LC' || worstVepAnnotation.lofFlags === 'NAGNAG_SITE') ? [
    ...[...new Set(worstVepAnnotation.lofFilter.split(/&|,/g))].map((lofFilterKey) => {
      const lofFilter = LOF_FILTER_MAP[lofFilterKey] || { message: lofFilterKey }
      return <div key={lofFilterKey}><b>LOFTEE: {lofFilter.title}</b><br />{lofFilter.message}.</div>
    }),
    worstVepAnnotation.lofFlags === 'NAGNAG_SITE' ?
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
          trigger={<a style={{ fontSize: '14px' }}>{vepGroup.replace(/_/g, ' ')}</a>}
        >
          {variant.genes.map(gene =>
            <div key={gene.geneId}>
              <Header size="large" attached="top" content={gene.symbol} subheader={`Gene Id: ${gene.geneId}`} />
              <Segment attached="bottom">
                <Table basic="very">
                  <Table.Body>
                    {vepAnnotations.filter(annotation => (annotation.gene || annotation.gene_id) !== gene.geneId).map(annotation =>
                      <Table.Row key={annotation.transcriptId}>
                        <Table.Cell width={3}>
                          <TranscriptLink
                            target="_blank"
                            href={`http://useast.ensembl.org/Homo_sapiens/Transcript/Summary?t=${annotation.transcriptId}`}
                            isChosen={annotation.isChosenTranscript}
                          >
                            {annotation.transcriptId}
                          </TranscriptLink>
                          <div>
                            {annotation.isChosenTranscript &&
                              <span>
                                <VerticalSpacer height={5} />
                                <Label content="Chosen Transcript" color="orange" size="small" />
                              </span>
                            }
                            {annotation.canonical &&
                              <span>
                                <VerticalSpacer height={5} />
                                <Label content="Canonical Transcript" color="green" size="small" />
                              </span>
                            }
                          </div>
                        </Table.Cell>
                        <Table.Cell width={4}>
                          {annotation.consequence}
                        </Table.Cell>
                        <Table.Cell width={9}>
                          <AnnotationSection>
                            <AnnotationLabel>Codons</AnnotationLabel>{annotation.codons}<br />
                            <AnnotationLabel>Amino Acids</AnnotationLabel>{annotation.aminoAcids}<br />
                          </AnnotationSection>
                          <AnnotationSection>
                            <AnnotationLabel>cDNA Position</AnnotationLabel>{annotation.cdnaPosition}<br />
                            <AnnotationLabel>CDS Position</AnnotationLabel>{annotation.cdsPosition}<br />
                          </AnnotationSection>
                          <AnnotationSection>
                            <AnnotationLabel>HGVS.C</AnnotationLabel>{annotation.hgvsc && <ProtenSequence hgvs={annotation.hgvsc} size="1em" />}<br />
                            <AnnotationLabel>HGVS.P</AnnotationLabel>{annotation.hgvsp && <ProtenSequence hgvs={annotation.hgvsp} size="1em" />}<br />
                          </AnnotationSection>
                        </Table.Cell>
                      </Table.Row>,
                    )}
                  </Table.Body>
                </Table>
              </Segment>
              <VerticalSpacer height={10} />
            </div>,
          )}
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
      { worstVepAnnotation.hgvsc &&
        <div>
          <b>HGVS.C</b><HorizontalSpacer width={5} /><ProtenSequence hgvs={worstVepAnnotation.hgvsc} />
        </div>
      }
      { worstVepAnnotation.hgvsp &&
        <div>
          <b>HGVS.P</b><HorizontalSpacer width={5} /><ProtenSequence hgvs={worstVepAnnotation.hgvsp} />
        </div>
      }
      <div>
        <a target="_blank" href={`https://www.google.com/search?q=${worstVepAnnotation.symbol}+${variations.join('+')}`}>google</a>
        <HorizontalSpacer width={5} />|<HorizontalSpacer width={5} />
        <a target="_blank" href={`https://www.ncbi.nlm.nih.gov/pubmed?term=${worstVepAnnotation.symbol} AND ( ${variations.join(' OR ')})`}>pubmed</a>
      </div>
    </div>
  )
}

Annotations.propTypes = {
  variant: PropTypes.object,
}

export default Annotations

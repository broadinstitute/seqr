import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Label, Header, Table, Segment } from 'semantic-ui-react'

import { loadVariantTranscripts } from 'redux/rootReducer'
import { getVariantIsLoading } from 'redux/selectors'
import { VerticalSpacer } from '../../Spacers'
import DataLoader from '../../DataLoader'
import { ProteinSequence } from './Annotations'


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

const Transcripts = ({ variant, loading, loadVariantTranscripts: dispatchLoadVariantTranscripts }) =>
  <DataLoader contentId={variant.variantId} content={variant.transcripts} loading={loading} load={dispatchLoadVariantTranscripts}>
    {variant.transcripts && variant.genes.map(gene =>
      <div key={gene.geneId}>
        <Header size="large" attached="top" content={gene.symbol} subheader={`Gene Id: ${gene.geneId}`} />
        <Segment attached="bottom">
          <Table basic="very">
            <Table.Body>
              {variant.transcripts[gene.geneId].map(transcript =>
                <Table.Row key={transcript.transcriptId}>
                  <Table.Cell width={3}>
                    <TranscriptLink
                      target="_blank"
                      href={`http://useast.ensembl.org/Homo_sapiens/Transcript/Summary?t=${transcript.transcriptId}`}
                      isChosen={transcript.isChosenTranscript}
                    >
                      {transcript.transcriptId}
                    </TranscriptLink>
                    <div>
                      {transcript.isChosenTranscript &&
                        <span>
                          <VerticalSpacer height={5} />
                          <Label content="Chosen Transcript" color="orange" size="small" />
                        </span>
                      }
                      {transcript.canonical &&
                        <span>
                          <VerticalSpacer height={5} />
                          <Label content="Canonical Transcript" color="green" size="small" />
                        </span>
                      }
                    </div>
                  </Table.Cell>
                  <Table.Cell width={4}>
                    {transcript.consequence}
                  </Table.Cell>
                  <Table.Cell width={9}>
                    <AnnotationSection>
                      <AnnotationLabel>Codons</AnnotationLabel>{transcript.codons}<br />
                      <AnnotationLabel>Amino Acids</AnnotationLabel>{transcript.aminoAcids}<br />
                    </AnnotationSection>
                    <AnnotationSection>
                      <AnnotationLabel>cDNA Position</AnnotationLabel>{transcript.cdnaPosition}<br />
                      <AnnotationLabel>CDS Position</AnnotationLabel>{transcript.cdsPosition}<br />
                    </AnnotationSection>
                    <AnnotationSection>
                      <AnnotationLabel>HGVS.C</AnnotationLabel>{transcript.hgvsc && <ProteinSequence hgvs={transcript.hgvsc} size="1em" />}<br />
                      <AnnotationLabel>HGVS.P</AnnotationLabel>{transcript.hgvsp && <ProteinSequence hgvs={transcript.hgvsp} size="1em" />}<br />
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
  </DataLoader>

Transcripts.propTypes = {
  variant: PropTypes.object.isRequired,
  loading: PropTypes.bool.isRequired,
  loadVariantTranscripts: PropTypes.func.isRequired,
}


const mapDispatchToProps = {
  loadVariantTranscripts,
}

const mapStateToProps = state => ({
  loading: getVariantIsLoading(state),
})

export default connect(mapStateToProps, mapDispatchToProps)(Transcripts)


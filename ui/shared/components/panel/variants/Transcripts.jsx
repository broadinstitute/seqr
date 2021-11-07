import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Label, Header, Table, Segment } from 'semantic-ui-react'

import { getGenesById } from 'redux/selectors'
import { updateVariantMainTranscript } from 'redux/rootReducer'
import { VerticalSpacer } from '../../Spacers'
import DispatchRequestButton from '../../buttons/DispatchRequestButton'
import ShowGeneModal from '../../buttons/ShowGeneModal'
import { ProteinSequence, TranscriptLink } from './VariantUtils'

const AnnotationSection = styled.div`
  display: inline-block;
  padding-right: 30px;
`

const AnnotationLabel = styled.small`
  font-weight: bolder;
  color: grey;
  padding-right: 10px;
`

const Transcripts = React.memo(({ variant, genesById, updateMainTranscript }) => (
  variant.transcripts && Object.entries(variant.transcripts).sort((transcriptsA, transcriptsB) => (
    Math.min(...transcriptsA[1].map(t => t.transcriptRank)) - Math.min(...transcriptsB[1].map(t => t.transcriptRank))
  )).map(([geneId, geneTranscripts]) => (
    <div key={geneId}>
      <Header
        size="huge"
        attached="top"
        content={genesById[geneId] && <ShowGeneModal gene={genesById[geneId]} modalId={`${variant.variantId}-transcripts`} />}
        subheader={`Gene Id: ${geneId}`}
      />
      <Segment attached="bottom">
        <Table basic="very">
          <Table.Body>
            {geneTranscripts.map(transcript => (
              <Table.Row key={transcript.transcriptId}>
                <Table.Cell width={3}>
                  <TranscriptLink variant={variant} transcript={transcript} />
                  <div>
                    {
                      transcript.transcriptRank === 0 && (
                        <span>
                          <VerticalSpacer height={5} />
                          <Label content="seqr Chosen Transcript" color="blue" size="small" />
                        </span>
                      )
                    }
                    {
                      transcript.canonical && (
                        <span>
                          <VerticalSpacer height={5} />
                          <Label content="Canonical Transcript" color="green" size="small" />
                        </span>
                      )
                    }
                    {
                      variant.variantGuid && (
                        <span>
                          <VerticalSpacer height={5} />
                          {
                            transcript.transcriptId === variant.selectedMainTranscriptId ?
                              <Label content="User Chosen Transcript" color="purple" size="small" /> : (
                                <DispatchRequestButton
                                  onSubmit={updateMainTranscript(transcript.transcriptId)}
                                  confirmDialog="Are you sure want to update the main transcript for this variant?"
                                >
                                  <Label as="a" content="Use as Main Transcript" color="violet" basic size="small" />
                                </DispatchRequestButton>
                              )
                          }
                        </span>
                      )
                    }
                  </div>
                </Table.Cell>
                <Table.Cell width={4}>
                  {transcript.majorConsequence}
                </Table.Cell>
                <Table.Cell width={9}>
                  <AnnotationSection>
                    <AnnotationLabel>Codons</AnnotationLabel>
                    {transcript.codons}
                    <br />
                    <AnnotationLabel>Amino Acids</AnnotationLabel>
                    {transcript.aminoAcids}
                    <br />
                  </AnnotationSection>
                  <AnnotationSection>
                    <AnnotationLabel>Biotype</AnnotationLabel>
                    {transcript.biotype}
                    <br />
                    <AnnotationLabel>cDNA Position</AnnotationLabel>
                    {transcript.cdnaPosition}
                    <br />
                  </AnnotationSection>
                  <AnnotationSection>
                    <AnnotationLabel>HGVS.C</AnnotationLabel>
                    {transcript.hgvsc && <ProteinSequence hgvs={transcript.hgvsc} />}
                    <br />
                    <AnnotationLabel>HGVS.P</AnnotationLabel>
                    {transcript.hgvsp && <ProteinSequence hgvs={transcript.hgvsp} />}
                    <br />
                  </AnnotationSection>
                </Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table>
      </Segment>
      <VerticalSpacer height={10} />
    </div>
  ))
))

Transcripts.propTypes = {
  variant: PropTypes.object.isRequired,
  genesById: PropTypes.object.isRequired,
  updateMainTranscript: PropTypes.func.isRequired,
}

const mapStateToProps = state => ({
  genesById: getGenesById(state),
})

const mapDispatchToProps = (dispatch, ownProps) => ({
  updateMainTranscript: transcriptId => () => (
    dispatch(updateVariantMainTranscript(ownProps.variant.variantGuid, transcriptId))
  ),
})

export default connect(mapStateToProps, mapDispatchToProps)(Transcripts)

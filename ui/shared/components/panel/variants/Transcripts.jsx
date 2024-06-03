import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Label, Header, Table, Segment } from 'semantic-ui-react'

import { getGenesById, getTranscriptsById, getFamiliesByGuid, getProjectsByGuid } from 'redux/selectors'
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

const HeaderLabel = AnnotationLabel.withComponent('span')

const TRANSCRIPT_LABELS = [
  {
    content: 'Canonical',
    color: 'green',
    shouldShow: transcript => transcript.canonical,
  },
  {
    content: 'MANE Select',
    color: 'teal',
    shouldShow: (transcript, transcriptsById) => transcriptsById[transcript.transcriptId]?.isManeSelect,
  },
  {
    content: 'seqr Chosen Transcript',
    color: 'blue',
    shouldShow: transcript => transcript.transcriptRank === 0,
  },
]

const Transcripts = React.memo(({ variant, genesById, transcriptsById, updateMainTranscript, project }) => (
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
                  {transcriptsById[transcript.transcriptId]?.refseqId && (
                    <div>
                      <HeaderLabel>RefSeq:</HeaderLabel>
                      <a
                        href={`https://www.ncbi.nlm.nih.gov/nuccore/${transcriptsById[transcript.transcriptId].refseqId}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {transcriptsById[transcript.transcriptId].refseqId}
                      </a>
                    </div>
                  )}
                  <div>
                    {TRANSCRIPT_LABELS.map(({ shouldShow, ...labelProps }) => (
                      shouldShow(transcript, transcriptsById) && (
                        <Label key={labelProps.content} size="small" horizontal {...labelProps} />
                      )
                    ))}
                    {
                      variant.variantGuid && project?.canEdit && (
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
                    <AnnotationLabel>Intron/Exon</AnnotationLabel>
                    {transcript.intron && `Intron ${transcript.intron.index}/${transcript.intron.total}`}
                    {transcript.exon && `${transcript.intron ? ', ' : ''}Exon ${transcript.exon.index}/${transcript.exon.total}`}
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
  transcriptsById: PropTypes.object.isRequired,
  updateMainTranscript: PropTypes.func.isRequired,
  project: PropTypes.object,
}

const mapStateToProps = (state, ownProps) => ({
  genesById: getGenesById(state),
  transcriptsById: getTranscriptsById(state),
  project: getProjectsByGuid(state)[getFamiliesByGuid(state)[ownProps.variant.familyGuids[0]]?.projectGuid],
})

const mapDispatchToProps = (dispatch, ownProps) => ({
  updateMainTranscript: transcriptId => () => (
    dispatch(updateVariantMainTranscript(ownProps.variant.variantGuid, transcriptId))
  ),
})

export default connect(mapStateToProps, mapDispatchToProps)(Transcripts)

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Label, Header, Table, Segment } from 'semantic-ui-react'

import { getGenesById } from 'redux/selectors'
import { VerticalSpacer } from '../../Spacers'
import ShowGeneModal from '../../buttons/ShowGeneModal'
import { ProteinSequence } from './Annotations'
import { GENOME_VERSION_37 } from '../../../utils/constants'


export const TranscriptLink = styled.a.attrs({
  target: '_blank',
  href: ({ variant, transcript }) => `http://${variant.genomeVersion === GENOME_VERSION_37 ? 'grch37' : 'useast'}.ensembl.org/Homo_sapiens/Transcript/Summary?t=${transcript.transcriptId}`,
  children: ({ transcript }) => transcript.transcriptId,
})`
  font-size: 1.3em;
  font-weight: ${(props) => { return props.isChosen ? 'bold' : 'normal' }}
`

const AnnotationSection = styled.div`
  display: inline-block;
  padding-right: 30px;
`

const AnnotationLabel = styled.small`
  font-weight: bolder;
  color: grey;
  padding-right: 10px;
`

const Transcripts = ({ variant, genesById }) =>
  variant.transcripts && Object.entries(variant.transcripts).sort((transcriptsA, transcriptsB) => (
    Math.min(...transcriptsA[1].map(t => t.transcriptRank)) - Math.min(...transcriptsB[1].map(t => t.transcriptRank))
  )).map(([geneId, geneTranscripts]) =>
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
            {geneTranscripts.map(transcript =>
              <Table.Row key={transcript.transcriptId}>
                <Table.Cell width={3}>
                  <TranscriptLink
                    variant={variant}
                    transcript={transcript}
                    isChosen={transcript.transcriptRank === 0}
                  />
                  <div>
                    {transcript.transcriptRank === 0 &&
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
                  {transcript.majorConsequence}
                </Table.Cell>
                <Table.Cell width={9}>
                  <AnnotationSection>
                    <AnnotationLabel>Codons</AnnotationLabel>{transcript.codons}<br />
                    <AnnotationLabel>Amino Acids</AnnotationLabel>{transcript.aminoAcids}<br />
                  </AnnotationSection>
                  <AnnotationSection>
                    <AnnotationLabel>Biotype</AnnotationLabel>{transcript.biotype}<br />
                    <AnnotationLabel>cDNA Position</AnnotationLabel>{transcript.cdnaPosition}<br />
                  </AnnotationSection>
                  <AnnotationSection>
                    <AnnotationLabel>HGVS.C</AnnotationLabel>{transcript.hgvsc && <ProteinSequence hgvs={transcript.hgvsc} />}<br />
                    <AnnotationLabel>HGVS.P</AnnotationLabel>{transcript.hgvsp && <ProteinSequence hgvs={transcript.hgvsp} />}<br />
                  </AnnotationSection>
                </Table.Cell>
              </Table.Row>,
            )}
          </Table.Body>
        </Table>
      </Segment>
      <VerticalSpacer height={10} />
    </div>,
  )

Transcripts.propTypes = {
  variant: PropTypes.object.isRequired,
  genesById: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  genesById: getGenesById(state),
})

export default connect(mapStateToProps)(Transcripts)


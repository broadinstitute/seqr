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
import { toCamelcase, camelcaseToTitlecase } from '../../../utils/stringUtils'

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

const AnnotationDetail = ({ consequence, title, getContent }) => (
  <span>
    <AnnotationLabel>{title}</AnnotationLabel>
    {getContent ? getContent(consequence) : consequence[toCamelcase(title)]}
    <br />
  </span>
)

AnnotationDetail.propTypes = {
  consequence: PropTypes.object.isRequired,
  title: PropTypes.string.isRequired,
  getContent: PropTypes.func,
}

export const ConsequenceDetails = (
  { consequences, variant, idField, idDetails, consequenceDetails, annotationSections, ensemblLink = {}, ...props },
) => (
  <Table basic="very">
    <Table.Body>
      {consequences.map(c => (
        <Table.Row key={c[idField]}>
          <Table.Cell width={3}>
            <TranscriptLink variant={variant} transcript={c} idField={idField} {...ensemblLink} />
            {idDetails && idDetails(c, variant, props)}
          </Table.Cell>
          <Table.Cell width={4}>
            {(c.consequenceTerms || [c.majorConsequence]).join('; ')}
            {consequenceDetails && consequenceDetails(c)}
          </Table.Cell>
          <Table.Cell width={9}>
            {annotationSections.map(([field1, field2]) => (
              <AnnotationSection key={field1.title}>
                <AnnotationDetail consequence={c} {...field1} />
                {field2 && <AnnotationDetail consequence={c} {...field2} />}
              </AnnotationSection>
            ))}
          </Table.Cell>
        </Table.Row>
      ))}
    </Table.Body>
  </Table>
)

ConsequenceDetails.propTypes = {
  consequences: PropTypes.arrayOf(PropTypes.object).isRequired,
  idField: PropTypes.string.isRequired,
  variant: PropTypes.object,
  idDetails: PropTypes.func,
  consequenceDetails: PropTypes.func,
  annotationSections: PropTypes.arrayOf(PropTypes.arrayOf(PropTypes.object)),
  ensemblLink: PropTypes.object,
}

export const isManeSelect = (transcript, transcriptsById) => (
  !!transcript.maneSelect || transcriptsById[transcript.transcriptId]?.isManeSelect
)

const TRANSCRIPT_LABELS = [
  {
    content: 'Canonical',
    color: 'green',
    shouldShow: transcript => transcript.canonical,
  },
  {
    content: 'MANE Select',
    color: 'teal',
    shouldShow: isManeSelect,
  },
  {
    content: 'MANE Plus Clinical',
    color: 'olive',
    shouldShow: transcript => !!transcript.manePlusClinical,
  },
  {
    content: 'seqr Chosen Transcript',
    color: 'blue',
    shouldShow: transcript => transcript.transcriptRank === 0,
  },
]

const RefseqLink = ({ refseqId }) => (refseqId ? (
  <div>
    <HeaderLabel>RefSeq:</HeaderLabel>
    <a
      href={`https://www.ncbi.nlm.nih.gov/nuccore/${refseqId}`}
      target="_blank"
      rel="noreferrer"
    >
      {refseqId}
    </a>
  </div>
) : null)

RefseqLink.propTypes = {
  refseqId: PropTypes.string,
}

const transcriptIdDetails = (transcript, variant, { transcriptsById, project, updateMainTranscript }) => (
  <div>
    <RefseqLink
      refseqId={
        transcript.maneSelect || transcript.manePlusClinical || transcript.refseqTranscriptId ||
        transcriptsById[transcript.transcriptId]?.refseqId
      }
    />
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
)

const transcriptConsequenceDetails = ({ utrannotator, spliceregion }) => (
  <div>
    {utrannotator?.fiveutrConsequence && <HeaderLabel>UTRAnnotator:</HeaderLabel>}
    {utrannotator?.fiveutrConsequence}
    {spliceregion?.extended_intronic_splice_region_variant && (
      <HeaderLabel>Extended Intronic Splice Region</HeaderLabel>
    )}
  </div>
)

const ANNOTATION_SECTIONS = [
  [{ title: 'Codons' }, { title: 'Amino Acids' }],
  [
    { title: 'Biotype' },
    {
      title: 'Intron/Exon',
      getContent: c => ['intron', 'exon'].filter(f => c[f]).map(f => `${camelcaseToTitlecase(f)} ${c[f].index}/${c[f].total}`).join(', '),
    },
  ],
  [
    { title: 'HGVS.C', getContent: transcript => transcript.hgvsc && <ProteinSequence hgvs={transcript.hgvsc} /> },
    { title: 'HGVS.P', getContent: transcript => transcript.hgvsp && <ProteinSequence hgvs={transcript.hgvsp} /> },
  ],
]

const Transcripts = React.memo(({ variant, genesById, ...props }) => (
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
        <ConsequenceDetails
          consequences={geneTranscripts}
          variant={variant}
          idField="transcriptId"
          idDetails={transcriptIdDetails}
          consequenceDetails={transcriptConsequenceDetails}
          annotationSections={ANNOTATION_SECTIONS}
          {...props}
        />
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

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { NavLink } from 'react-router-dom'
import { Label, Popup, List, Header, Segment, Divider, Table, Button, Loader } from 'semantic-ui-react'

import { getGenesById, getLocusListsByGuid, getRnaSeqDataByFamilyGene } from 'redux/selectors'
import {
  MISSENSE_THRESHHOLD, LOF_THRESHHOLD, PANEL_APP_CONFIDENCE_LEVEL_COLORS,
  PANEL_APP_CONFIDENCE_DESCRIPTION,
} from '../../../utils/constants'
import { camelcaseToTitlecase } from '../../../utils/stringUtils'
import { HorizontalSpacer, VerticalSpacer } from '../../Spacers'
import { InlineHeader, ButtonLink, ColoredLabel } from '../../StyledComponents'
import { GeneSearchLink } from '../../buttons/SearchResultsLink'
import ShowGeneModal from '../../buttons/ShowGeneModal'
import Modal from '../../modal/Modal'

const RnaSeqTpm = React.lazy(() => import('./RnaSeqTpm'))

const CONSTRAINED_GENE_RANK_THRESHOLD = 1000
const HI_THRESHOLD = 0.84
const TS_THRESHOLD = 0.993

const INLINE_STYLE = {
  display: 'inline-block',
}

const PADDED_INLINE_STYLE = {
  marginTop: '0.5em',
  ...INLINE_STYLE,
}

const BaseGeneLabelContent = styled(({ color, customColor, label, maxWidth, containerStyle, dispatch, ...props }) => {
  const labelProps = {
    ...props,
    size: 'mini',
    content: label,
  }
  return customColor ?
    <ColoredLabel {...labelProps} color={customColor} /> : <Label {...labelProps} color={color || 'grey'} />
})`
   margin: ${props => props.margin || '0px .5em .8em 0px'} !important;
   overflow: hidden;
   text-overflow: ellipsis;
   white-space: nowrap;
   max-width: ${props => props.maxWidth || 'none'};
`
const GeneLabelContent = props => <BaseGeneLabelContent {...props} />

const GeneLinks = styled.div`
  font-size: .9em;
  display: inline-block;
  padding-right: 10px;
  padding-bottom: .5em;
`

const ListItemLink = styled(List.Item).attrs({ icon: 'linkify' })`
 .content {
    color: initial;
    cursor: auto;
 }
 
 i.icon {
  color: #4183C4 !important;
 }
`

const GeneLabel = React.memo(({ popupHeader, popupContent, showEmpty, ...labelProps }) => {
  const content = <GeneLabelContent {...labelProps} />
  return (popupContent || showEmpty) ?
    <Popup header={popupHeader} trigger={content} content={popupContent} size="tiny" wide hoverable /> : content
})

GeneLabel.propTypes = {
  label: PropTypes.string.isRequired,
  popupHeader: PropTypes.string.isRequired,
  popupContent: PropTypes.oneOfType([PropTypes.string, PropTypes.node]).isRequired,
  showEmpty: PropTypes.bool,
}

const BaseLocusListLabels = React.memo((
  { locusListGuids, locusListsByGuid, locusListConfidence, compact, containerStyle, ...labelProps },
) => (
  compact ? (
    <GeneDetailSection
      compact
      color="teal"
      compactLabel="Gene Lists"
      details={
        locusListGuids.length > 0 &&
          <List bulleted items={locusListGuids.map(locusListGuid => locusListsByGuid[locusListGuid].name)} />
      }
    />
  ) : (
    <div style={containerStyle}>
      {locusListGuids.map((locusListGuid) => {
        const panelAppConfidence = locusListConfidence && locusListConfidence[locusListGuid]
        let { description } = locusListsByGuid[locusListGuid] || {}
        if (panelAppConfidence) {
          description = (
            <div>
              {description}
              <br />
              <br />
              <b>PanelApp gene confidence: &nbsp;</b>
              {PANEL_APP_CONFIDENCE_DESCRIPTION[panelAppConfidence]}
            </div>
          )
        }
        return (
          <GeneDetailSection
            key={locusListGuid}
            color="teal"
            customColor={panelAppConfidence && PANEL_APP_CONFIDENCE_LEVEL_COLORS[panelAppConfidence]}
            maxWidth="7em"
            showEmpty
            label={(locusListsByGuid[locusListGuid] || {}).name}
            description={(locusListsByGuid[locusListGuid] || {}).name}
            details={description}
            containerStyle={containerStyle}
            {...labelProps}
          />
        )
      })}
    </div>
  )))

BaseLocusListLabels.propTypes = {
  locusListGuids: PropTypes.arrayOf(PropTypes.string).isRequired,
  locusListConfidence: PropTypes.object,
  compact: PropTypes.bool,
  locusListsByGuid: PropTypes.object.isRequired,
  containerStyle: PropTypes.object,
}

BaseLocusListLabels.defaultProps = {
  compact: false,
  containerStyle: null,
}

const mapLocusListStateToProps = state => ({
  locusListsByGuid: getLocusListsByGuid(state),
})

export const LocusListLabels = connect(mapLocusListStateToProps)(BaseLocusListLabels)

const GeneDetailSection = React.memo(({ details, compact, description, compactLabel, showEmpty, ...labelProps }) => {
  if (!details && !showEmpty) {
    return null
  }

  return compact ? (
    <div>
      <VerticalSpacer height={10} />
      <Label size="tiny" color={labelProps.color} content={`${compactLabel || description}:`} />
      <HorizontalSpacer width={10} />
      {details}
    </div>
  ) : <GeneLabel popupHeader={description} popupContent={details} showEmpty={showEmpty} {...labelProps} />
})

GeneDetailSection.propTypes = {
  details: PropTypes.node,
  compact: PropTypes.bool,
  color: PropTypes.string,
  description: PropTypes.string,
  label: PropTypes.string,
  compactLabel: PropTypes.string,
  showEmpty: PropTypes.bool,
}

const GENCC_COLORS = {
  Definitive: '#276749',
  Strong: '#38a169',
  Moderate: '#68d391',
  Supportive: '#63b3ed',
  Limited: '#fc8181',
}

const GENE_DISEASE_DETAIL_SECTIONS = [
  {
    color: 'violet',
    description: 'GenCC',
    label: 'GENCC',
    showDetails: gene => gene.genCc?.classifications,
    detailsDisplay: gene => (
      <List>
        {gene.genCc.classifications.sort(
          (a, b) => b.date.localeCompare(a.date),
        ).map(({ classification, disease, moi, date, submitter }) => (
          <ListItemLink
            key={submitter}
            content={(
              <span>
                <ColoredLabel horizontal size="mini" color={GENCC_COLORS[classification] || 'grey'} content={classification} />
                <b>{submitter}</b>
                {` (${date.split('-')[0]}): ${disease}`}
                <i>{` (${moi})`}</i>
              </span>
            )}
            target="_blank"
            href={`https://search.thegencc.org/genes/${gene.genCc.hgncId}`}
          />
        ))}
      </List>
    ),
  },
  {
    color: 'orange',
    description: 'Disease Phenotypes',
    label: 'IN OMIM',
    expandedLabel: 'OMIM',
    compactLabel: 'OMIM Disease Phenotypes',
    expandedDisplay: true,
    showDetails: gene => gene.omimPhenotypes.length > 0,
    detailsDisplay: gene => (
      <List>
        {gene.omimPhenotypes.map(phenotype => (
          <ListItemLink
            key={phenotype.phenotypeDescription}
            content={phenotype.phenotypeInheritance ? (
              <span>
                {phenotype.phenotypeDescription}
                <i>{` (${phenotype.phenotypeInheritance})`}</i>
              </span>
            ) : phenotype.phenotypeDescription}
            target="_blank"
            href={`https://www.omim.org/entry/${phenotype.phenotypeMimNumber}`}
          />
        ))}
      </List>
    ),
  },
]

const RNA_SEQ_DETAIL_FIELDS = ['zScore', 'pValue', 'pAdjust']

const GENE_DETAIL_SECTIONS = [
  {
    color: 'red',
    description: 'Missense Constraint',
    label: 'MISSENSE CONSTR',
    showDetails: gene => (
      (gene.constraints.misZ && gene.constraints.misZ > MISSENSE_THRESHHOLD) ||
      (gene.constraints.misZRank && gene.constraints.misZRank < CONSTRAINED_GENE_RANK_THRESHOLD)
    ),
    detailsDisplay: gene => (
      `This gene ranks ${gene.constraints.misZRank} most constrained out of
      ${gene.constraints.totalGenes} genes under study in terms of missense constraint (z-score:
      ${gene.constraints.misZ.toPrecision(4)}). Missense contraint is a measure of the degree to which the number
      of missense variants found in this gene in ExAC v0.3 is higher or lower than expected according to the
      statistical model described in [K. Samocha 2014]. In general this metric is most useful for genes that act
      via a dominant mechanism, and where a large proportion of the protein is heavily functionally constrained.`),
  },
  {
    color: 'red',
    description: 'Loss of Function Constraint',
    label: 'LOF CONSTR',
    showDetails: gene => gene.constraints.louef < LOF_THRESHHOLD,
    detailsDisplay: gene => (
      `This gene ranks as ${gene.constraints.louefRank} most intolerant of LoF mutations out of
       ${gene.constraints.totalGenes} genes under study (louef:
       ${gene.constraints.louef.toPrecision(4)}${gene.constraints.pli ? `, pLi: ${gene.constraints.pli.toPrecision(4)}` : ''}).
       LOEUF is the observed to expected upper bound fraction for loss-of-function variants based on the variation
       observed in the gnomad data. Both LOEUF and pLi are measures of how likely the gene is to be intolerant of
       loss-of-function mutations`),
  },
  {
    color: 'red',
    description: 'HaploInsufficient',
    label: 'HI',
    showDetails: gene => gene.cnSensitivity.phi && gene.cnSensitivity.phi > HI_THRESHOLD,
    detailsDisplay: gene => (
      `These are a score under development by the Talkowski lab that predict whether a gene is haploinsufficient based 
      on large chromosomal microarray data set analysis. Scores >0.84 are considered to have high likelihood to be 
      haploinsufficient. This gene has a score of ${gene.cnSensitivity.phi.toPrecision(4)}.`),
  },
  {
    color: 'red',
    description: 'TriploSensitive',
    label: 'TS',
    showDetails: gene => gene.cnSensitivity.pts && gene.cnSensitivity.pts > TS_THRESHOLD,
    detailsDisplay: gene => (
      `These are a score under development by the Talkowski lab that predict whether a gene is triplosensitive based on
       large chromosomal microarray dataset analysis. Scores >0.993 are considered to have high likelihood to be 
       triplosensitive. This gene has a score of ${gene.cnSensitivity.pts.toPrecision(4)}.`),
  },
  {
    color: 'pink',
    description: 'RNA-Seq Outlier',
    label: 'RNA-Seq',
    showDetails: (gene, rnaSeqData) => rnaSeqData?.significantOutliers && rnaSeqData.significantOutliers[gene.geneId],
    detailsDisplay: (gene, rnaSeqData) => (
      <div>
        This gene is flagged as an outlier for RNA-Seq in the following samples
        <Table basic="very" compact="very">
          <Table.Header>
            <Table.Row>
              <Table.HeaderCell />
              {RNA_SEQ_DETAIL_FIELDS.map(
                field => <Table.HeaderCell key={field}>{camelcaseToTitlecase(field).replace(' ', '-')}</Table.HeaderCell>,
              )}
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {Object.entries(rnaSeqData.significantOutliers[gene.geneId]).map(([individual, data]) => (
              <Table.Row key={individual}>
                <Table.HeaderCell>{individual}</Table.HeaderCell>
                {RNA_SEQ_DETAIL_FIELDS.map(
                  field => <Table.Cell key={field}>{data[field].toPrecision(3)}</Table.Cell>,
                )}
              </Table.Row>
            ))}
          </Table.Body>
        </Table>
      </div>
    ),
  },
]

const OmimSegments = styled(Segment.Group).attrs({ size: 'tiny', horizontal: true, compact: true })`
  width: 100%;
  max-height: 6em;
  overflow-y: auto;
  display: inline-flex !important;
  margin-top: 0 !important;
  margin-bottom: 5px !important;
  
  .segment {
    border-left: none !important;
  }
  
  .segment:first-child {
    max-width: 4em;
  }
`

const getDetailSections = (configs, gene, compact, labelProps, rnaSeqData) => configs.map(
  ({ showDetails, detailsDisplay, ...sectionConfig }) => (
    { ...sectionConfig, detail: showDetails(gene, rnaSeqData) && detailsDisplay(gene, rnaSeqData) }),
).filter(({ detail }) => detail).map(({ detail, expandedDisplay, ...sectionConfig }) => (
  (expandedDisplay && !compact) ? (
    <OmimSegments key={sectionConfig.label}>
      <Segment color={sectionConfig.color}>
        <Label size="mini" color={sectionConfig.color} content={sectionConfig.expandedLabel} />
      </Segment>
      <Segment color={sectionConfig.color}>
        {detail}
      </Segment>
    </OmimSegments>
  ) : (
    <GeneDetailSection
      key={sectionConfig.label}
      compact={compact}
      details={detail}
      {...sectionConfig}
      {...labelProps}
    />
  )
))

export const GeneDetails = React.memo((
  { gene, compact, showLocusLists, containerStyle, rnaSeqData, ...labelProps },
) => {
  const geneDetails = getDetailSections(GENE_DETAIL_SECTIONS, gene, compact, labelProps, rnaSeqData)
  const hasLocusLists = showLocusLists && gene.locusListGuids.length > 0
  const showDivider = geneDetails.length > 0 && hasLocusLists

  return (
    <div style={containerStyle}>
      {geneDetails}
      {showDivider && <Divider fitted />}
      {
        hasLocusLists && (
          <LocusListLabels
            locusListGuids={gene.locusListGuids}
            locusListConfidence={gene.locusListConfidence}
            compact={compact}
            containerStyle={showDivider ? PADDED_INLINE_STYLE : INLINE_STYLE}
            {...labelProps}
          />
        )
      }
      <br />
      {getDetailSections(GENE_DISEASE_DETAIL_SECTIONS, gene, compact, labelProps)}
    </div>
  )
})

GeneDetails.propTypes = {
  gene: PropTypes.object,
  compact: PropTypes.bool,
  showLocusLists: PropTypes.bool,
  containerStyle: PropTypes.object,
  rnaSeqData: PropTypes.object,
}

const GeneSearchLinkWithPopup = props => (
  <Popup
    trigger={
      <GeneSearchLink {...props} />
    }
    content="Search for all variants with AF < 10% in this gene present in any affected individual"
    size="tiny"
  />
)

export const getGeneConsequence = (geneId, variant) => {
  const geneTranscripts = variant.transcripts[geneId]
  return geneTranscripts && geneTranscripts.length > 0 &&
    (geneTranscripts[0].majorConsequence || '').replace(/_/g, ' ')
}

const BaseVariantGene = React.memo((
  { geneId, gene, variant, compact, showInlineDetails, compoundHetToggle, rnaSeqData },
) => {
  const geneConsequence = getGeneConsequence(geneId, variant)

  if (!gene) {
    return <InlineHeader size="medium" content={geneId} subheader={geneConsequence} />
  }

  const compactDetails = compact && !showInlineDetails

  const geneDetails = (
    <GeneDetails
      gene={gene}
      compact={compactDetails}
      containerStyle={showInlineDetails ? INLINE_STYLE : null}
      margin={showInlineDetails ? '1em .5em 0px 0px' : null}
      horizontal={showInlineDetails}
      rnaSeqData={rnaSeqData}
      showLocusLists
    />
  )

  let summaryDetail
  if (compact) {
    summaryDetail = showInlineDetails ? (
      <span>
        {geneConsequence}
        &nbsp; &nbsp;
        {geneDetails}
      </span>
    ) : geneConsequence
  } else {
    summaryDetail = (
      <GeneLinks>
        <a href={`https://decipher.sanger.ac.uk/gene/${gene.geneId}/overview/protein-genomic-info`} target="_blank" rel="noreferrer">
          Decipher
        </a>
        &nbsp; | &nbsp;
        <Popup
          trigger={<NavLink to={`/summary_data/saved_variants/ALL/${gene.geneId}`} target="_blank">seqr</NavLink>}
          content="Show all previously saved variants in this gene across all your seqr projects"
          size="tiny"
        />
        &nbsp; | &nbsp;
        <GeneSearchLinkWithPopup location={geneId} familyGuids={variant.familyGuids} />
      </GeneLinks>
    )
  }

  const geneSummary = (
    <div>
      <ShowGeneModal gene={gene} fontWeight="bold" size={compact ? 'large' : 'huge'} modalId={variant.variantId} />
      <HorizontalSpacer width={10} />
      {summaryDetail}
      {compoundHetToggle && compoundHetToggle(gene.geneId)}
    </div>
  )

  return compactDetails ? (
    <Popup
      header="Gene Details"
      size="tiny"
      position="bottom left"
      wide
      hoverable
      trigger={geneSummary}
      content={geneDetails}
    />
  ) : (
    <div>
      {geneSummary}
      {!showInlineDetails && geneDetails}
      {rnaSeqData?.tpms && rnaSeqData.tpms[gene.geneId] && (
        <Modal
          trigger={<Button basic compact color="blue" size="mini" content="Show Gene Expression" />}
          title={`${gene.geneSymbol} Expression`}
          modalName={`${variant.variantId}-${gene.geneId}-tpm`}
        >
          <React.Suspense fallback={<Loader />}>
            <RnaSeqTpm geneId={geneId} tpms={rnaSeqData.tpms[gene.geneId]} />
          </React.Suspense>
        </Modal>
      )}
    </div>
  )
})

BaseVariantGene.propTypes = {
  geneId: PropTypes.string.isRequired,
  gene: PropTypes.object.isRequired,
  variant: PropTypes.object.isRequired,
  compact: PropTypes.bool,
  showInlineDetails: PropTypes.bool,
  compoundHetToggle: PropTypes.func,
  rnaSeqData: PropTypes.object,
}

const mapStateToProps = (state, ownProps) => ({
  gene: getGenesById(state)[ownProps.geneId],
  rnaSeqData: getRnaSeqDataByFamilyGene(state)[ownProps.variant.familyGuids[0]],
})

export const VariantGene = connect(mapStateToProps)(BaseVariantGene)

class VariantGenes extends React.PureComponent {

  static propTypes = {
    variant: PropTypes.object.isRequired,
    mainGeneId: PropTypes.string,
    genesById: PropTypes.object.isRequired,
    rnaSeqData: PropTypes.object,
  }

  static defaultProps = {
    mainGeneId: null,
  }

  state = { showAll: false }

  showGenes = () => {
    this.setState({ showAll: true })
  }

  render() {
    const { variant, genesById, mainGeneId, rnaSeqData } = this.props
    const { showAll } = this.state
    const geneIds = Object.keys(variant.transcripts || {})

    const geneSearchLink = !mainGeneId && geneIds.length > 0 &&
      <GeneSearchLinkWithPopup location={geneIds.join(',')} familyGuids={variant.familyGuids} padding="10px 0" />

    if (geneIds.length < 6 || showAll) {
      return (
        <div>
          {geneIds.filter(geneId => geneId !== mainGeneId).map(geneId => (
            <BaseVariantGene
              key={geneId}
              geneId={geneId}
              gene={genesById[geneId]}
              variant={variant}
              rnaSeqData={rnaSeqData}
              showInlineDetails={!mainGeneId}
              compact
            />
          ))}
          {geneSearchLink}
        </div>
      )
    }

    const genes = geneIds.map(geneId => genesById[geneId]).filter(gene => gene)
    const geneConsequences = [...(new Set(geneIds.map(
      geneId => (variant.transcripts[geneId][0] || {}).majorConsequence,
    ).filter(consequence => consequence).map(consequence => consequence.replace(/_/g, ' '))))].join(', ')

    return (
      <div>
        <ButtonLink fontWeight="bold" size="large" onClick={this.showGenes}>{`${geneIds.length} Genes`}</ButtonLink>
        {geneConsequences}
        <VerticalSpacer height={10} />
        <div>
          {[...GENE_DISEASE_DETAIL_SECTIONS, ...GENE_DETAIL_SECTIONS].map(
            ({ showDetails, detailsDisplay, ...sectionConfig }) => {
              const sectionGenes = genes.filter(gene => showDetails(gene))
              return (
                <GeneDetailSection
                  key={sectionConfig.label}
                  details={sectionGenes.length > 0 && sectionGenes.map(gene => (
                    <div key={gene.geneId}>
                      <Header size="small" content={gene.geneSymbol} />
                      {detailsDisplay(gene, rnaSeqData)}
                      <VerticalSpacer height={5} />
                    </div>
                  ))}
                  {...sectionConfig}
                />
              )
            },
          )}
        </div>
        {geneSearchLink}
      </div>
    )
  }

}

const mapAllGenesStateToProps = (state, ownProps) => ({
  genesById: getGenesById(state),
  rnaSeqData: getRnaSeqDataByFamilyGene(state)[ownProps.variant.familyGuids[0]],
})

export default connect(mapAllGenesStateToProps)(VariantGenes)

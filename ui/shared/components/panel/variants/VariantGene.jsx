import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { NavLink } from 'react-router-dom'
import { Label, Popup, List, Header, Segment } from 'semantic-ui-react'

import { getGenesById, getLocusListsByGuid } from 'redux/selectors'
import { MISSENSE_THRESHHOLD, LOF_THRESHHOLD, ANY_AFFECTED } from '../../../utils/constants'
import { HorizontalSpacer, VerticalSpacer } from '../../Spacers'
import { InlineHeader, ButtonLink } from '../../StyledComponents'
import SearchResultsLink from '../../buttons/SearchResultsLink'
import ShowGeneModal from '../../buttons/ShowGeneModal'

const CONSTRAINED_GENE_RANK_THRESHOLD = 1000
const HI_THRESHOLD = 0.84
const TS_THRESHOLD = 0.993

const INLINE_STYLE = {
  display: 'inline-block',
}

const BaseGeneLabelContent = styled(
  ({ color, label, maxWidth, containerStyle, dispatch, ...props }) => <Label {...props} size="mini" color={color || 'grey'} content={label} />,
)`
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
  color: PropTypes.string,
  popupHeader: PropTypes.string,
  popupContent: PropTypes.oneOfType([PropTypes.string, PropTypes.node]),
  showEmpty: PropTypes.bool,
}

const BaseLocusListLabels = React.memo(({ locusListGuids, locusListsByGuid, compact, containerStyle, ...labelProps }) => (
  compact ?
    <GeneDetailSection
      compact
      color="teal"
      compactLabel="Gene Lists"
      details={locusListGuids.length > 0 &&
        <List bulleted items={locusListGuids.map(locusListGuid => locusListsByGuid[locusListGuid].name)} />
      }
    /> :
    <div style={containerStyle}>
      <React.Fragment>
        {locusListGuids.map(locusListGuid =>
          <GeneDetailSection
            key={locusListGuid}
            color="teal"
            maxWidth="7em"
            showEmpty
            label={(locusListsByGuid[locusListGuid] || {}).name}
            description={(locusListsByGuid[locusListGuid] || {}).name}
            details={(locusListsByGuid[locusListGuid] || {}).description}
            containerStyle={containerStyle}
            {...labelProps}
          />,
        )}
      </React.Fragment>
    </div>),
)

BaseLocusListLabels.propTypes = {
  locusListGuids: PropTypes.array.isRequired,
  compact: PropTypes.bool,
  locusListsByGuid: PropTypes.object,
  containerStyle: PropTypes.object,
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

const OMIM_SECTION = {
  color: 'orange',
  description: 'Disease Phenotypes',
  label: 'IN OMIM',
  compactLabel: 'OMIM Disease Phenotypes',
  showDetails: gene => gene.omimPhenotypes.length > 0,
  detailsDisplay: gene =>
    <List>
      {gene.omimPhenotypes.map(phenotype =>
        <ListItemLink
          key={phenotype.phenotypeDescription}
          content={phenotype.phenotypeInheritance ?
            <span>{phenotype.phenotypeDescription} (<i>{phenotype.phenotypeInheritance}</i>)</span> :
            phenotype.phenotypeDescription}
          target="_blank"
          href={`https://www.omim.org/entry/${phenotype.phenotypeMimNumber}`}
        />,
      )}
    </List>,
}

const GENE_DETAIL_SECTIONS = [
  {
    color: 'red',
    description: 'Missense Constraint',
    label: 'MISSENSE CONSTR',
    showDetails: gene => (
      (gene.constraints.misZ && gene.constraints.misZ > MISSENSE_THRESHHOLD) ||
      (gene.constraints.misZRank && gene.constraints.misZRank < CONSTRAINED_GENE_RANK_THRESHOLD)
    ),
    detailsDisplay: gene =>
      `This gene ranks ${gene.constraints.misZRank} most constrained out of
      ${gene.constraints.totalGenes} genes under study in terms of missense constraint (z-score:
      ${gene.constraints.misZ.toPrecision(4)}). Missense contraint is a measure of the degree to which the number
      of missense variants found in this gene in ExAC v0.3 is higher or lower than expected according to the
      statistical model described in [K. Samocha 2014]. In general this metric is most useful for genes that act
      via a dominant mechanism, and where a large proportion of the protein is heavily functionally constrained.`,
  },
  {
    color: 'red',
    description: 'Loss of Function Constraint',
    label: 'LOF CONSTR',
    showDetails: gene => gene.constraints.louef < LOF_THRESHHOLD,
    detailsDisplay: gene =>
      `This gene ranks as ${gene.constraints.louefRank} most intolerant of LoF mutations out of
       ${gene.constraints.totalGenes} genes under study (louef:
       ${gene.constraints.louef.toPrecision(4)}${gene.constraints.pli ? `, pLi: ${gene.constraints.pli.toPrecision(4)}` : ''}).
       LOEUF is the observed to expected upper bound fraction for loss-of-function variants based on the variation
       observed in the gnomad data. Both LOEUF and pLi are measures of how likely the gene is to be intolerant of
       loss-of-function mutations`,
  },
  {
    color: 'red',
    description: 'HaploInsufficient',
    label: 'HI',
    showDetails: gene => gene.cnSensitivity.phi && gene.cnSensitivity.phi > HI_THRESHOLD,
    detailsDisplay: gene =>
      `These are a score under development by the Talkowski lab that predict whether a gene is haploinsufficient based 
      on large chromosomal microarray data set analysis. Scores >0.84 are considered to have high likelihood to be 
      haploinsufficient. This gene has a score of ${gene.cnSensitivity.phi.toPrecision(4)}.`,
  },
  {
    color: 'red',
    description: 'TriploSensitive',
    label: 'TS',
    showDetails: gene => gene.cnSensitivity.pts && gene.cnSensitivity.pts > TS_THRESHOLD,
    detailsDisplay: gene =>
      `These are a score under development by the Talkowski lab that predict whether a gene is triplosensitive based on
       large chromosomal microarray dataset analysis. Scores >0.993 are considered to have high likelihood to be 
       triplosensitive. This gene has a score of ${gene.cnSensitivity.pts.toPrecision(4)}.`,
  },
]

const OmimSegments = styled(Segment.Group).attrs({ size: 'tiny', horizontal: true, compact: true })`
  max-height: 6em;
  overflow-y: auto;
  display: inline-flex !important;
  margin: 0 !important;
  
  .segment {
    border-left: none !important;
  }
  
  .segment:first-child {
    max-width: 4em;
  }
`

export const GeneDetails = React.memo(({ gene, compact, showLocusLists, containerStyle, ...labelProps }) => {
  const omimDetails = OMIM_SECTION.showDetails(gene) && OMIM_SECTION.detailsDisplay(gene)
  return (
    <div style={containerStyle}>
      {GENE_DETAIL_SECTIONS.map(({ showDetails, detailsDisplay, ...sectionConfig }) =>
        <GeneDetailSection
          key={sectionConfig.label}
          compact={compact}
          details={showDetails(gene) && detailsDisplay(gene)}
          {...sectionConfig}
          {...labelProps}
        />,
      )}
      {showLocusLists && gene.locusListGuids.length > 0 &&
        <LocusListLabels locusListGuids={gene.locusListGuids} compact={compact} containerStyle={INLINE_STYLE} {...labelProps} />
      }
      {omimDetails && (compact ?
        <GeneDetailSection compact details={omimDetails} {...OMIM_SECTION} {...labelProps} /> :
        <OmimSegments>
          <Segment color={OMIM_SECTION.color}>
            <Label size="mini" color={OMIM_SECTION.color} content="OMIM" />
          </Segment>
          <Segment color={OMIM_SECTION.color}>
            {omimDetails}
          </Segment>
        </OmimSegments>
      )}
    </div>
  )
},
)

GeneDetails.propTypes = {
  gene: PropTypes.object,
  compact: PropTypes.bool,
  showLocusLists: PropTypes.bool,
  containerStyle: PropTypes.object,
}

const BaseVariantGene = React.memo(({ geneId, gene, variant, compact, showInlineDetails, areCompoundHets }) => {

  const geneTranscripts = variant.transcripts[geneId]
  const geneConsequence = geneTranscripts && geneTranscripts.length > 0 && (geneTranscripts[0].majorConsequence || '').replace(/_/g, ' ')

  if (!gene) {
    return <InlineHeader size="medium" content={geneId} subheader={geneConsequence} />
  }

  const compactDetails = compact && !showInlineDetails

  const geneDetails = (
    <GeneDetails
      gene={gene}
      compact={compactDetails}
      containerStyle={(showInlineDetails || areCompoundHets) && INLINE_STYLE}
      margin={showInlineDetails ? '1em .5em 0px 0px' : null}
      horizontal={showInlineDetails}
      showLocusLists
    />
  )

  let summaryDetail
  if (compact) {
    summaryDetail = showInlineDetails ? <span>{geneDetails} {geneConsequence}</span> : geneConsequence
  } else {
    summaryDetail = (
      <GeneLinks>
        <a href={`https://decipher.sanger.ac.uk/gene/${gene.geneId}/overview/protein-genomic-info`} target="_blank">Decipher</a>
        <HorizontalSpacer width={5} />|<HorizontalSpacer width={5} />
        <Popup
          trigger={<NavLink to={`/summary_data/saved_variants/ALL/${gene.geneId}`} target="_blank">seqr</NavLink>}
          content="Show all previously saved variants in this gene across all your seqr projects"
          size="tiny"
        />
        <HorizontalSpacer width={5} />|<HorizontalSpacer width={5} />
        <Popup
          trigger={<SearchResultsLink location={gene.geneId} familyGuids={variant.familyGuids} inheritanceMode={ANY_AFFECTED} />}
          content="Search for all variants in this gene present in any affected individual"
          size="tiny"
        />
      </GeneLinks>
    )
  }

  const geneSummary = (
    <div>
      <ShowGeneModal gene={gene} fontWeight="bold" size={compact ? 'large' : 'huge'} modalId={variant.variantId} />
      <HorizontalSpacer width={10} />
      {summaryDetail}
    </div>
  )

  return compactDetails ?
    <Popup
      header="Gene Details"
      size="tiny"
      position="bottom left"
      wide
      hoverable
      trigger={geneSummary}
      content={geneDetails}
    /> : (
      <div>
        {geneSummary}
        {!showInlineDetails && geneDetails}
      </div>
    )
})

BaseVariantGene.propTypes = {
  geneId: PropTypes.string.isRequired,
  gene: PropTypes.object,
  variant: PropTypes.object.isRequired,
  compact: PropTypes.bool,
  showInlineDetails: PropTypes.bool,
  areCompoundHets: PropTypes.bool,
}

const mapStateToProps = (state, ownProps) => ({
  gene: getGenesById(state)[ownProps.geneId],
})

export const VariantGene = connect(mapStateToProps)(BaseVariantGene)


class VariantGenes extends React.PureComponent {

  static propTypes = {
    variant: PropTypes.object,
    mainGeneId: PropTypes.string,
    genesById: PropTypes.object,
  }

  constructor(props) {
    super(props)

    this.state = { showAll: Object.keys(props.variant.transcripts || {}).length < 6 }
  }

  showGenes = () => {
    this.setState({ showAll: true })
  }

  render() {
    const { variant, genesById, mainGeneId } = this.props
    const geneIds = Object.keys(variant.transcripts || {})

    if (this.state.showAll) {
      return (
        <div>
          {geneIds.filter(geneId => geneId !== mainGeneId).map(geneId =>
            <BaseVariantGene
              key={geneId}
              geneId={geneId}
              gene={genesById[geneId]}
              variant={variant}
              showInlineDetails={!mainGeneId}
              compact
            />,
          )}
          {!mainGeneId && geneIds.length > 0 &&
            <SearchResultsLink location={geneIds.join(',')} familyGuids={variant.familyGuids} padding="10px 0" />
          }
        </div>
      )
    }

    const genes = geneIds.map(geneId => genesById[geneId]).filter(gene => gene)

    return (
      <div>
        <ButtonLink fontWeight="bold" size="large" onClick={this.showGenes}>{geneIds.length} Genes</ButtonLink>
        <VerticalSpacer height={10} />
        <div>
          {[OMIM_SECTION, ...GENE_DETAIL_SECTIONS].map(({ showDetails, detailsDisplay, ...sectionConfig }) => {
            const sectionGenes = genes.filter(gene => showDetails(gene))
            return (
              <GeneDetailSection
                key={sectionConfig.label}
                details={sectionGenes.length > 0 && sectionGenes.map(gene =>
                  <div key={gene.geneId}>
                    <Header size="small" content={gene.geneSymbol} />
                    {detailsDisplay(gene)}
                    <VerticalSpacer height={5} />
                  </div>,
                )}
                {...sectionConfig}
              />
            )
        })}
        </div>
      </div>
    )
  }
}

const mapAllGenesStateToProps = state => ({
  genesById: getGenesById(state),
})


export default connect(mapAllGenesStateToProps)(VariantGenes)

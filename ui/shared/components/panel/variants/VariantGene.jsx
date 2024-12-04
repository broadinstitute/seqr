import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { NavLink } from 'react-router-dom'
import { Label, Popup, List, Header, Segment, Divider, Table, Button, Loader } from 'semantic-ui-react'

import { getGenesById, getLocusListsByGuid, getFamiliesByGuid } from 'redux/selectors'
import DataTable from 'shared/components/table/DataTable'
import { panelAppUrl, moiToMoiInitials } from '../../../utils/panelAppUtils'
import {
  MISSENSE_THRESHHOLD,
  LOF_THRESHHOLD,
  PANEL_APP_CONFIDENCE_LEVEL_COLORS,
  PANEL_APP_CONFIDENCE_DESCRIPTION,
  getDecipherGeneLink,
} from '../../../utils/constants'
import { compareObjects } from '../../../utils/sortUtils'
import { camelcaseToTitlecase } from '../../../utils/stringUtils'
import { BehindModalPopup } from '../../PopupWithModal'
import { HorizontalSpacer, VerticalSpacer } from '../../Spacers'
import { InlineHeader, NoBorderTable, ButtonLink, ColoredLabel } from '../../StyledComponents'
import { PermissiveGeneSearchLink } from '../../buttons/SearchResultsLink'
import ShowGeneModal from '../../buttons/ShowGeneModal'
import Modal from '../../modal/Modal'
import { GenCC, ClingenLabel, HI_THRESHOLD, TS_THRESHOLD, SHET_THRESHOLD } from '../genes/GeneDetail'
import { getIndividualGeneDataByFamilyGene } from './selectors'

const RnaSeqTpm = React.lazy(() => import('./RnaSeqTpm'))

const CONSTRAINED_GENE_RANK_THRESHOLD = 1000

const BaseGeneLabelContent = styled(({ color, customColor, label, maxWidth, dispatch, ...props }) => {
  const labelProps = {
    ...props,
    size: 'mini',
    content: <span>{label}</span>,
  }

  return customColor ?
    <ColoredLabel {...labelProps} color={customColor} /> : <Label {...labelProps} color={color || 'grey'} />
})`
  margin: ${props => props.margin || '0px .5em .8em 0px'} !important;
  white-space: nowrap;

  span {
    display: inline-block;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: ${props => props.maxWidth || 'none'};
  }

  .detail {
    margin-left: 0.5em !important;

    &::before {
      content: "(";
    }
    &::after {
      content: ")";
    }
  }
`
export const GeneLabelContent = props => <BaseGeneLabelContent {...props} />

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

const LocusListDivider = styled(Divider).attrs({ fitted: true })`
  margin-bottom: 0.5em !important;
`

const LocusListsContainer = styled.div`
  max-height: 10.2em;
  overflow-y: auto;
`

// Fixes popup location for elements in scrollable containers (i.e. locus lists in LocusListsContainer)
// Suggested fix for known issue from https://github.com/Semantic-Org/Semantic-UI-React/issues/3687
const POPPER_MODIFIERS = { preventOverflow: { boundariesElement: 'window' } }

const GeneLabel = React.memo(({ popupHeader, popupContent, showEmpty, ...labelProps }) => {
  const content = <GeneLabelContent {...labelProps} />
  return (popupContent || showEmpty) ?
    <Popup header={popupHeader} trigger={content} content={popupContent} size="tiny" wide hoverable popperModifiers={POPPER_MODIFIERS} /> : content
})

GeneLabel.propTypes = {
  label: PropTypes.string.isRequired,
  popupHeader: PropTypes.string.isRequired,
  popupContent: PropTypes.oneOfType([PropTypes.string, PropTypes.node]).isRequired,
  showEmpty: PropTypes.bool,
}

const PanelAppHoverOver = ({ url, locusListDescription, confidence, initials, moi }) => (
  <div>
    <a target="_blank" href={url} rel="noreferrer">{locusListDescription}</a>
    <br />
    <br />
    <b>PanelApp gene confidence: &nbsp;</b>
    {PANEL_APP_CONFIDENCE_DESCRIPTION[confidence]}
    <br />
    <br />
    <b>PanelApp mode of inheritance: </b>
    {initials}
    {' '}
    {moi}
  </div>
)

PanelAppHoverOver.propTypes = {
  url: PropTypes.string.isRequired,
  locusListDescription: PropTypes.string.isRequired,
  confidence: PropTypes.string.isRequired,
  initials: PropTypes.string.isRequired,
  moi: PropTypes.string.isRequired,
}

function getPaProps({ panelAppDetails, locusListDescription, paLocusList, geneSymbol }) {
  if (!panelAppDetails || !paLocusList || !geneSymbol) {
    return {
      initials: null,
      description: locusListDescription,
      customColor: false,
    }
  }

  const { url, panelAppId } = paLocusList
  const fullUrl = panelAppUrl(url, panelAppId, geneSymbol)
  const moi = panelAppDetails.moi || 'Unknown'
  const confidence = panelAppDetails.confidence || 'Unknown'
  const initials = moiToMoiInitials(moi).join(', ') || null

  const description = PanelAppHoverOver({
    url: fullUrl,
    locusListDescription,
    confidence,
    initials,
    moi,
  })

  return {
    initials,
    description,
    customColor: PANEL_APP_CONFIDENCE_LEVEL_COLORS[panelAppDetails.confidence],
  }
}

const BaseLocusListLabels = React.memo(({
  locusListGuids, locusListsByGuid, panelAppDetail, geneSymbol, compact, showInlineDetails, ...labelProps
}) => {
  const locusListSectionProps = {
    compact, color: 'teal', compactLabel: 'Gene Lists',
  }

  const locusLists = locusListGuids.map(locusListGuid => ({
    panelAppDetails: panelAppDetail && panelAppDetail[locusListGuid], ...locusListsByGuid[locusListGuid],
  })).sort(compareObjects('name')).sort(
    (a, b) => (b.panelAppDetails?.confidence || 0) - (a.panelAppDetails?.confidence || 0),
  )

  if (compact) {
    return (
      <GeneDetailSection
        {...locusListSectionProps}
        details={
          locusListGuids.length > 0 &&
            <List bulleted items={locusLists.map(({ name }) => name)} />
        }
      />
    )
  }
  const labels = locusLists.map((locusList) => {
    const { locusListGuid, name: label, description: locusListDescription, paLocusList, panelAppDetails } = locusList
    const { description, initials, customColor } = (panelAppDetails && paLocusList) ? getPaProps({
      panelAppDetails,
      locusListDescription,
      paLocusList,
      geneSymbol,
    }) : {
      description: locusListDescription,
      initials: false,
      customColor: false,
    }
    return (
      <GeneDetailSection
        key={locusListGuid}
        customColor={customColor}
        detail={initials}
        maxWidth="8em"
        showEmpty
        label={label}
        description={label}
        details={description}
        {...locusListSectionProps}
        {...labelProps}
      />
    )
  })
  return showInlineDetails ? labels : <LocusListsContainer>{labels}</LocusListsContainer>
})

BaseLocusListLabels.propTypes = {
  locusListGuids: PropTypes.arrayOf(PropTypes.string).isRequired,
  panelAppDetail: PropTypes.object,
  geneSymbol: PropTypes.string,
  compact: PropTypes.bool,
  showInlineDetails: PropTypes.bool,
  locusListsByGuid: PropTypes.object.isRequired,
}

BaseLocusListLabels.defaultProps = {
  compact: false,
}

const mapLocusListStateToProps = state => ({
  locusListsByGuid: getLocusListsByGuid(state),
})

const LocusListLabels = connect(mapLocusListStateToProps)(BaseLocusListLabels)

const ClinGenRow = ({ value, label, href }) => (
  <Table.Row>
    <Table.Cell textAlign="right"><ClingenLabel value={value} /></Table.Cell>
    <Table.Cell><a target="_blank" rel="noreferrer" href={href}>{label}</a></Table.Cell>
  </Table.Row>
)

ClinGenRow.propTypes = {
  value: PropTypes.string,
  label: PropTypes.string,
  href: PropTypes.string,
}

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

export const omimPhenotypesDetail = (phenotypes, showCoordinates) => (
  <List>
    {phenotypes.map(phenotype => (
      <ListItemLink
        key={phenotype.phenotypeDescription}
        content={(
          <span>
            {phenotype.phenotypeDescription}
            {phenotype.phenotypeInheritance && <i>{` (${phenotype.phenotypeInheritance})`}</i>}
            {showCoordinates && ` ${phenotype.chrom}:${phenotype.start}-${phenotype.end}`}
          </span>
        )}
        target="_blank"
        href={`https://www.omim.org/entry/${phenotype.phenotypeMimNumber}`}
      />
    ))}
  </List>
)

const GENE_DISEASE_DETAIL_SECTIONS = [
  {
    color: 'violet',
    description: 'GenCC',
    label: 'GENCC',
    showDetails: gene => gene.genCc?.classifications,
    detailsDisplay: gene => (<GenCC genCc={gene.genCc} />),
  },
  {
    color: 'purple',
    description: 'ClinGen Dosage Sensitivity',
    label: 'ClinGen',
    showDetails: gene => gene.clinGen,
    detailsDisplay: gene => (
      <NoBorderTable basic="very" compact="very">
        {gene.clinGen.haploinsufficiency &&
          <ClinGenRow value={gene.clinGen.haploinsufficiency} href={gene.clinGen.href} label="Haploinsufficiency" />}
        {gene.clinGen.triplosensitivity &&
          <ClinGenRow value={gene.clinGen.triplosensitivity} href={gene.clinGen.href} label="Triplosensitivity" />}
      </NoBorderTable>
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
    detailsDisplay: gene => omimPhenotypesDetail(gene.omimPhenotypes),
  },
]

const RNA_SEQ_DETAIL_FIELDS = ['zScore', 'pValue', 'pAdjust']

const INDIVIDUAL_NAME_COLUMN = { name: 'individualName', content: '', format: ({ individualName }) => (<b>{individualName}</b>) }

const RNA_SEQ_COLUMNS = [
  INDIVIDUAL_NAME_COLUMN,
  ...RNA_SEQ_DETAIL_FIELDS.map(name => (
    { name, content: camelcaseToTitlecase(name).replace(' ', '-'), format: row => row[name].toPrecision(3) }
  )),
]

const PHENOTYPE_GENE_INFO_COLUMNS = [
  INDIVIDUAL_NAME_COLUMN,
  {
    name: 'diseaseName',
    content: 'Disease',
    format: ({ diseaseName, diseaseId }) => (
      <div>
        {diseaseName}
        <br />
        <i>{diseaseId}</i>
      </div>
    ),
  },
  { name: 'rank', content: 'Rank' },
  {
    name: 'scores',
    content: 'Scores',
    format: ({ scores }) => Object.keys(scores).sort().map(scoreName => (
      <div key={scoreName}>
        <b>{camelcaseToTitlecase(scoreName)}</b>
        : &nbsp;
        { scores[scoreName].toPrecision(3) }
      </div>
    )),
  },
]

const HOVER_DATA_TABLE_PROPS = { basic: 'very', compact: 'very', singleLine: true }

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
    showDetails: gene => (gene.constraints.louef < LOF_THRESHHOLD) ||
      (gene.cnSensitivity.phi && gene.cnSensitivity.phi > HI_THRESHOLD) ||
      (gene.sHet.postMean && gene.sHet.postMean > SHET_THRESHOLD),
    detailsDisplay: gene => (
      <List bulleted>
        {gene.constraints.louef < LOF_THRESHHOLD && (
          <List.Item>
            This gene ranks as &nbsp;
            {gene.constraints.louefRank}
            &nbsp;most intolerant of LoF mutations out of &nbsp;
            {gene.constraints.totalGenes}
            &nbsp;genes under study (louef: &nbsp;
            {gene.constraints.louef.toPrecision(4)}
            {gene.constraints.pli ? `, pLi: ${gene.constraints.pli.toPrecision(4)}` : ''}
            )
            <a href="https://pubmed.ncbi.nlm.nih.gov/32461654/" target="_blank" rel="noreferrer"> Karczewski (2020)</a>
          </List.Item>
        )}
        {gene.sHet.postMean > SHET_THRESHOLD && (
          <List.Item>
            This gene has a Shet score of &nbsp;
            {gene.sHet.postMean.toPrecision(4)}
            <a href="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10245655" target="_blank" rel="noreferrer"> Zeng (2023)</a>
          </List.Item>
        )}
        {gene.cnSensitivity.phi > HI_THRESHOLD && (
          <List.Item>
            This gene has a haploinsufficiency (HI) score of &nbsp;
            {gene.cnSensitivity.phi.toPrecision(4)}
            <a href="https://pubmed.ncbi.nlm.nih.gov/35917817" target="_blank" rel="noreferrer"> Collins (2022)</a>
          </List.Item>
        )}
      </List>
    ),
  },
  {
    color: 'red',
    description: 'TriploSensitive',
    label: 'TS',
    showDetails: gene => gene.cnSensitivity.pts && gene.cnSensitivity.pts > TS_THRESHOLD,
    detailsDisplay: gene => (
      `These are a score developed by the Talkowski lab that predict whether a gene is triplosensitive based on
       large chromosomal microarray dataset analysis. Scores >${TS_THRESHOLD} are considered to have high likelihood to be 
       triplosensitive. This gene has a score of ${gene.cnSensitivity.pts.toPrecision(4)}.`),
  },
  {
    color: 'pink',
    description: 'RNA-Seq Expression Outlier',
    label: 'RNA expression',
    showDetails: (gene, indivGeneData) => indivGeneData?.rnaSeqData && indivGeneData.rnaSeqData[gene.geneId],
    detailsDisplay: (gene, indivGeneData) => (
      <div>
        This gene is flagged as an outlier for RNA-Seq in the following samples
        <DataTable
          {...HOVER_DATA_TABLE_PROPS}
          data={indivGeneData.rnaSeqData[gene.geneId]}
          idField="individualName"
          columns={RNA_SEQ_COLUMNS}
        />
      </div>
    ),
  },
  {
    color: 'orange',
    description: 'Phenotype Prioritization',
    label: 'Prioritized-Gene', // required for using the label as a key and won't be displayed
    showDetails: (gene, indivGeneData) => indivGeneData?.phenotypeGeneScores &&
      indivGeneData.phenotypeGeneScores[gene.geneId],
    detailsDisplay: (gene, indivGeneData) => (Object.entries(indivGeneData.phenotypeGeneScores[gene.geneId]).map(
      ([tool, data]) => ({
        label: tool.toUpperCase(),
        detail: (
          <DataTable
            {...HOVER_DATA_TABLE_PROPS}
            data={data}
            idField="rowId"
            columns={PHENOTYPE_GENE_INFO_COLUMNS}
            defaultSortColumn="rank"
          />
        ),
      }),
    )),
  },
]

const OmimSegments = styled(Segment.Group).attrs({ size: 'tiny', horizontal: true, compact: true })`
  width: 100%;
  max-height: 6em;
  overflow-y: auto;
  display: inline-flex !important;
  margin-top: 0 !important;
  margin-bottom: 5px !important;
  
  resize: vertical;
  &[style*="height"] {
    max-height: unset; 
  }
  
  .segment {
    border-left: none !important;
  }
  
  .segment:first-child {
    max-width: 4em;
  }
`

const getDetailSections = (configs, gene, compact, labelProps, individualGeneData, noExpand) => configs.map(
  ({ showDetails, detailsDisplay, ...sectionConfig }) => (
    {
      ...sectionConfig,
      detail: showDetails(gene, individualGeneData) && detailsDisplay(gene, individualGeneData),
    }),
).filter(({ detail }) => detail).reduce((acc, config) => (Array.isArray(config.detail) ?
  [
    ...acc,
    ...config.detail.map(detail => ({ ...config, ...detail })),
  ] : [...acc, config]),
[]).map(({ detail, expandedDisplay, expandedLabel, ...sectionConfig }) => (
  (expandedDisplay && !compact && !noExpand) ? (
    <OmimSegments key={sectionConfig.label}>
      <Segment color={sectionConfig.color}>
        <Label size="mini" color={sectionConfig.color} content={expandedLabel} />
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
  { gene, compact, showLocusLists, showInlineDetails, individualGeneData, noExpand, ...labelProps },
) => {
  const geneDetails = getDetailSections(GENE_DETAIL_SECTIONS, gene, compact, labelProps, individualGeneData)
  const geneDiseaseDetails = getDetailSections(GENE_DISEASE_DETAIL_SECTIONS, gene, compact, labelProps, null, noExpand)
  const hasLocusLists = showLocusLists && gene.locusListGuids?.length > 0
  const showDivider = !showInlineDetails && geneDetails.length > 0 && (hasLocusLists || geneDiseaseDetails.length > 0)

  return [
    ...geneDetails,
    showDivider && <LocusListDivider key="divider" />,
    hasLocusLists && (
      <LocusListLabels
        key="locusLists"
        geneSymbol={gene.geneSymbol}
        locusListGuids={gene.locusListGuids}
        panelAppDetail={gene.panelAppDetail}
        compact={compact}
        showInlineDetails={showInlineDetails}
        {...labelProps}
      />
    ),
    ...geneDiseaseDetails,
    !showInlineDetails && geneDiseaseDetails.length > 0 && <br key="br" />,
  ]
})

GeneDetails.propTypes = {
  gene: PropTypes.object,
  compact: PropTypes.bool,
  showLocusLists: PropTypes.bool,
  showInlineDetails: PropTypes.bool,
  noExpand: PropTypes.bool,
  individualGeneData: PropTypes.object,
}

const GeneSearchLinkWithPopup = props => (
  <Popup
    trigger={
      <PermissiveGeneSearchLink {...props} />
    }
    content="Search for all variants with AF < 3% in this gene present in any affected individual"
    size="tiny"
  />
)

const getGeneConsequence = (geneId, variant) => {
  const geneTranscripts = (variant.transcripts || {})[geneId]
  return geneTranscripts && geneTranscripts.length > 0 &&
    (geneTranscripts[0].majorConsequence || '').replace(/_/g, ' ')
}

export const BaseVariantGene = React.memo(({
  geneId, gene, variant, compact, showInlineDetails, compoundHetToggle, tpmGenes, individualGeneData, geneModalId,
  noExpand, geneSearchFamily, hideLocusLists,
}) => {
  const geneConsequence = variant && getGeneConsequence(geneId, variant)

  if (!gene) {
    return <InlineHeader size="medium" content={geneId} subheader={geneConsequence} />
  }

  const compactDetails = compact && !showInlineDetails

  const geneDetails = (
    <GeneDetails
      gene={gene}
      compact={compactDetails}
      showInlineDetails={showInlineDetails}
      noExpand={noExpand}
      margin={showInlineDetails ? '1em .5em 0px 0px' : null}
      horizontal={showInlineDetails}
      individualGeneData={individualGeneData}
      showLocusLists={!hideLocusLists}
    />
  )

  let summaryDetail
  if (compact) {
    summaryDetail = showInlineDetails ? (
      <span>
        {geneSearchFamily &&
          <GeneSearchLinkWithPopup location={geneId} familyGuid={geneSearchFamily} buttonText="" icon="search" size="tiny" />}
        {geneConsequence}
        &nbsp; &nbsp;
        {geneDetails}
      </span>
    ) : geneConsequence
  } else {
    summaryDetail = (
      <GeneLinks>
        <a href={getDecipherGeneLink(gene)} target="_blank" rel="noreferrer">
          Decipher
        </a>
        &nbsp; | &nbsp;
        <Popup
          trigger={<NavLink to={`/summary_data/saved_variants/ALL/${gene.geneId}`} target="_blank">seqr</NavLink>}
          content="Show all previously saved variants in this gene across all your seqr projects"
          size="tiny"
        />
        &nbsp; | &nbsp;
        {!variant.lookupFamilyGuids && <GeneSearchLinkWithPopup location={geneId} familyGuids={variant.familyGuids} />}
      </GeneLinks>
    )
  }

  const geneSummary = (
    <div>
      <ShowGeneModal gene={gene} fontWeight="bold" size={compact ? 'large' : 'huge'} modalId={geneModalId || variant.variantId} />
      <HorizontalSpacer width={10} />
      {summaryDetail}
      {compoundHetToggle && compoundHetToggle(gene.geneId)}
    </div>
  )

  return compactDetails ? (
    <BehindModalPopup
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
      {tpmGenes && tpmGenes.includes(gene.geneId) && (
        <Modal
          trigger={<Button basic compact color="blue" size="mini" content="Show Gene Expression" />}
          title={`${gene.geneSymbol} Expression`}
          modalName={`${variant.variantId}-${gene.geneId}-tpm`}
        >
          <React.Suspense fallback={<Loader />}>
            <RnaSeqTpm geneId={geneId} familyGuid={variant.familyGuids[0]} />
          </React.Suspense>
        </Modal>
      )}
    </div>
  )
})

const RNA_SEQ_PROP_TYPES = {
  tpmGenes: PropTypes.arrayOf(PropTypes.string),
  individualGeneData: PropTypes.object,
}

BaseVariantGene.propTypes = {
  geneId: PropTypes.string.isRequired,
  gene: PropTypes.object.isRequired,
  variant: PropTypes.object,
  compact: PropTypes.bool,
  showInlineDetails: PropTypes.bool,
  compoundHetToggle: PropTypes.func,
  geneModalId: PropTypes.string,
  noExpand: PropTypes.bool,
  geneSearchFamily: PropTypes.string,
  hideLocusLists: PropTypes.bool,
  ...RNA_SEQ_PROP_TYPES,
}

const getRnaSeqProps = (state, ownProps) => ({
  tpmGenes: getFamiliesByGuid(state)[ownProps.variant.familyGuids[0]]?.tpmGenes,
  individualGeneData: getIndividualGeneDataByFamilyGene(state)[ownProps.variant.familyGuids[0]],
})

const mapStateToProps = (state, ownProps) => ({
  gene: getGenesById(state)[ownProps.geneId],
  ...getRnaSeqProps(state, ownProps),
})

export const VariantGene = connect(mapStateToProps)(BaseVariantGene)

class VariantGenes extends React.PureComponent {

  static propTypes = {
    variant: PropTypes.object.isRequired,
    mainGeneId: PropTypes.string,
    genesById: PropTypes.object.isRequired,
    showMainGene: PropTypes.bool,
    ...RNA_SEQ_PROP_TYPES,
  }

  static defaultProps = {
    mainGeneId: null,
  }

  state = { showAll: false }

  showGenes = () => {
    this.setState({ showAll: true })
  }

  render() {
    const { variant, genesById, mainGeneId, showMainGene, individualGeneData, tpmGenes } = this.props
    const { showAll } = this.state
    const geneIds = Object.keys(variant.transcripts || {})
    const genes = geneIds.map(geneId => genesById[geneId]).filter(gene => gene)

    const geneSearchLink = !mainGeneId && geneIds.length > 0 &&
      <GeneSearchLinkWithPopup location={geneIds.join(',')} familyGuids={variant.familyGuids} padding="10px 0" />

    if (geneIds.length < 6 || showAll) {
      return (
        <div>
          {genes.filter(({ geneId }) => showMainGene || geneId !== mainGeneId).sort(
            (a, b) => a.startGrch38 - b.startGrch38,
          ).map(gene => (
            <BaseVariantGene
              key={gene.geneId}
              geneId={gene.geneId}
              gene={gene}
              variant={variant}
              individualGeneData={individualGeneData}
              tpmGenes={tpmGenes}
              showInlineDetails={!mainGeneId}
              compact
            />
          ))}
          {geneSearchLink}
        </div>
      )
    }

    const geneConsequences = [...(new Set(geneIds.map(
      geneId => (variant.transcripts[geneId][0] || {}).majorConsequence,
    ).filter(consequence => consequence).map(consequence => consequence.replace(/_/g, ' '))))].join(', ')

    return (
      <div>
        <ButtonLink fontWeight="bold" size="large" onClick={this.showGenes}>{`${geneIds.length} Genes`}</ButtonLink>
        {geneConsequences}
        <VerticalSpacer height={10} />
        {!mainGeneId && (
          <div>
            {[...GENE_DISEASE_DETAIL_SECTIONS, ...GENE_DETAIL_SECTIONS].map(
              ({ showDetails, detailsDisplay, expandedDisplay, expandedLabel, ...sectionConfig }) => {
                const sectionGenes = genes.filter(gene => showDetails(gene))
                return (
                  <GeneDetailSection
                    key={sectionConfig.label}
                    details={sectionGenes.length > 0 && sectionGenes.map(gene => (
                      <div key={gene.geneId}>
                        <Header size="small" content={gene.geneSymbol} />
                        {detailsDisplay(gene, individualGeneData)}
                        <VerticalSpacer height={5} />
                      </div>
                    ))}
                    {...sectionConfig}
                  />
                )
              },
            )}
          </div>
        )}
        {geneSearchLink}
      </div>
    )
  }

}

const mapAllGenesStateToProps = (state, ownProps) => ({
  genesById: getGenesById(state),
  ...getRnaSeqProps(state, ownProps),
})

export default connect(mapAllGenesStateToProps)(VariantGenes)

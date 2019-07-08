import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Label, Popup, List } from 'semantic-ui-react'

import { getGenesById, getLocusListsByGuid, getCurrentProject } from 'redux/selectors'
import { MISSENSE_THRESHHOLD, LOF_THRESHHOLD } from '../../../utils/constants'
import { HorizontalSpacer, VerticalSpacer } from '../../Spacers'
import { InlineHeader } from '../../StyledComponents'
import SearchResultsLink from '../../buttons/SearchResultsLink'
import ShowGeneModal from '../../buttons/ShowGeneModal'

const CONSTRAINED_GENE_RANK_THRESHOLD = 1000

const GeneLabelContent = styled(
  ({ color, label, maxWidth, ...props }) => <Label {...props} size="mini" color={color || 'grey'} content={label} />,
)`
   margin: ${props => props.margin || '0px .5em .8em 0px'} !important;
   overflow: hidden;
   text-overflow: ellipsis;
   white-space: nowrap;
   max-width: ${props => props.maxWidth || 'none'};
`

const GeneLinks = styled.div`
  font-size: .9em;
  display: inline-block;
  padding-right: 10px;
  padding-bottom: .5em;
`

const ListItemLink = styled(List.Item).attrs({ as: 'a', icon: 'linkify' })`
 .content {
    color: initial;
    cursor: auto;
 }
 
 i.icon {
  color: #4183C4 !important;
 }
`

const GeneLabel = ({ popupHeader, popupContent, showEmpty, ...labelProps }) => {
  const content = <GeneLabelContent {...labelProps} />
  return (popupContent || showEmpty) ?
    <Popup header={popupHeader} trigger={content} content={popupContent} size="tiny" wide hoverable /> : content
}

GeneLabel.propTypes = {
  label: PropTypes.string.isRequired,
  color: PropTypes.string,
  popupHeader: PropTypes.string,
  popupContent: PropTypes.oneOfType([PropTypes.string, PropTypes.node]),
  showEmpty: PropTypes.bool,
}

const BaseLocusListLabels = ({ locusListGuids, locusListsByGuid, compact }) => (
  compact ?
    <GeneDetailSection
      compact
      color="teal"
      compactLabel="Gene Lists"
      details={locusListGuids.length > 0 &&
        <List bulleted items={locusListGuids.map(locusListGuid => locusListsByGuid[locusListGuid].name)} />
      }
    /> :
    <div>
      {locusListGuids.map(locusListGuid =>
        <GeneDetailSection
          key={locusListGuid}
          color="teal"
          maxWidth="7em"
          showEmpty
          label={(locusListsByGuid[locusListGuid] || {}).name}
          description={(locusListsByGuid[locusListGuid] || {}).name}
          details={(locusListsByGuid[locusListGuid] || {}).description}
        />,
      )}
    </div>
)

BaseLocusListLabels.propTypes = {
  locusListGuids: PropTypes.array.isRequired,
  compact: PropTypes.bool,
  locusListsByGuid: PropTypes.object,
}

const mapLocusListStateToProps = state => ({
  locusListsByGuid: getLocusListsByGuid(state),
})

export const LocusListLabels = connect(mapLocusListStateToProps)(BaseLocusListLabels)


const GeneDetailSection = ({ details, compact, description, compactLabel, showEmpty, ...labelProps }) => {
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
}

GeneDetailSection.propTypes = {
  details: PropTypes.node,
  compact: PropTypes.bool,
  color: PropTypes.string,
  description: PropTypes.string,
  label: PropTypes.string,
  compactLabel: PropTypes.string,
  showEmpty: PropTypes.bool,
}

export const GeneDetails = ({ gene, compact, showLocusLists, ...labelProps }) =>
  <div>
    <GeneDetailSection
      compact={compact}
      color="orange"
      description="Disease Phenotypes"
      label="IN OMIM"
      compactLabel="OMIM Disease Phenotypes"
      details={gene.omimPhenotypes.length > 0 &&
        <List>
          {gene.omimPhenotypes.map(phenotype =>
            <ListItemLink
              key={phenotype.phenotypeDescription}
              content={phenotype.phenotypeDescription}
              target="_blank"
              href={`https://www.omim.org/entry/${phenotype.phenotypeMimNumber}`}
            />,
          )}
        </List>}
      {...labelProps}
    />
    <GeneDetailSection
      compact={compact}
      color="red"
      label="MISSENSE CONSTR"
      description="Missense Constraint"
      details={((gene.constraints.misZ && gene.constraints.misZ > MISSENSE_THRESHHOLD) ||
        (gene.constraints.misZRank && gene.constraints.misZRank < CONSTRAINED_GENE_RANK_THRESHOLD)) &&
        `This gene ranks ${gene.constraints.misZRank} most constrained out of
        ${gene.constraints.totalGenes} genes under study in terms of missense constraint (z-score:
        ${gene.constraints.misZ.toPrecision(4)}). Missense contraint is a measure of the degree to which the number
        of missense variants found in this gene in ExAC v0.3 is higher or lower than expected according to the
        statistical model described in [K. Samocha 2014]. In general this metric is most useful for genes that act
        via a dominant mechanism, and where a large proportion of the protein is heavily functionally constrained.`}
      {...labelProps}
    />
    <GeneDetailSection
      compact={compact}
      color="red"
      label="LOF CONSTR"
      description="Loss of Function Constraint"
      details={gene.constraints.louef < LOF_THRESHHOLD &&
        `This gene ranks as ${gene.constraints.louefRank} most intolerant of LoF mutations out of
         ${gene.constraints.totalGenes} genes under study (louef:
         ${gene.constraints.louef.toPrecision(4)}${gene.constraints.pli ? `, pLi: ${gene.constraints.pli.toPrecision(4)}` : ''}).
         LOEUF is the observed to expected upper bound fraction for loss-of-function variants based on the variation
         observed in the gnomad data. Both LOEUF and pLi are measures of how likely the gene is to be intolerant of
         loss-of-function mutations`}
      {...labelProps}
    />
    {showLocusLists && <LocusListLabels locusListGuids={gene.locusListGuids} compact={compact} />}
  </div>

GeneDetails.propTypes = {
  gene: PropTypes.object,
  compact: PropTypes.bool,
  showLocusLists: PropTypes.bool,
}

const VariantGene = ({ geneId, gene, project, variant, compact }) => {

  const geneConsequence = variant.transcripts[geneId] && variant.transcripts[geneId][0].majorConsequence.replace(/_/g, ' ')

  if (!gene) {
    return <InlineHeader size="medium" content={geneId} subheader={geneConsequence} />
  }

  const geneSummary = (
    <div>
      <ShowGeneModal gene={gene} fontWeight="bold" size={compact ? 'large' : 'huge'} modalId={variant.variantId} />
      <HorizontalSpacer width={10} />
      {compact ? geneConsequence :
      <GeneLinks>
        <a href={`http://gnomad.broadinstitute.org/gene/${gene.geneSymbol}`} target="_blank">gnomAD</a>
        <HorizontalSpacer width={5} />|<HorizontalSpacer width={5} />
        {project && !project.hasNewSearch ?
          <a href={`/project/${project.deprecatedProjectId}/gene/${gene.geneId}`} target="_blank" rel="noopener noreferrer">Gene Search</a> :
          <SearchResultsLink geneId={gene.geneId} familyGuids={variant.familyGuids} />}
      </GeneLinks>}
    </div>
  )

  const geneDetails = <GeneDetails gene={gene} compact={compact} showLocusLists />

  return compact ?
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
        {geneDetails}
      </div>
    )
}

VariantGene.propTypes = {
  geneId: PropTypes.string.isRequired,
  project: PropTypes.object,
  gene: PropTypes.object,
  variant: PropTypes.object.isRequired,
  compact: PropTypes.bool,
}

const mapStateToProps = (state, ownProps) => ({
  project: getCurrentProject(state),
  gene: getGenesById(state)[ownProps.geneId],
})

export default connect(mapStateToProps)(VariantGene)

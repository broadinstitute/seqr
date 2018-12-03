import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Label, Popup, List } from 'semantic-ui-react'

import { getProject } from 'pages/Project/selectors'
import { getGenesById } from 'redux/selectors'
import { HorizontalSpacer, VerticalSpacer } from '../../Spacers'
import ShowGeneModal from '../../buttons/ShowGeneModal'

const CONSTRAINED_GENE_RANK_THRESHOLD = 1000

const GeneLabelContent = styled(Label).attrs({
  size: 'mini',
  color: props => props.color || 'grey',
  content: props => props.label,
})`
   margin: 0px .5em .8em 0px !important;
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

const GeneLabel = ({ popupHeader, popupContent, ...labelProps }) => {
  const content = <GeneLabelContent {...labelProps} />
  return popupContent ? <Popup header={popupHeader} trigger={content} content={popupContent} size="tiny" wide hoverable /> : content
}

GeneLabel.propTypes = {
  label: PropTypes.string.isRequired,
  color: PropTypes.string,
  popupHeader: PropTypes.string,
  popupContent: PropTypes.oneOfType([PropTypes.string, PropTypes.node]),
}

export const LocusListLabels = ({ locusLists, compact }) => {
  const locusListLabelProps = {
    color: 'teal',
    description: 'Gene Lists',
    compact,
    details: locusLists.length > 0 && <List bulleted items={locusLists} />,
  }
  return (
    compact ? <GeneDetailSection {...locusListLabelProps} /> :
    <div>
      {locusLists.map(geneListName =>
        <GeneDetailSection
          key={geneListName}
          label={`${geneListName.substring(0, 10)}${geneListName.length > 10 ? ' ...' : ''}`}
          {...locusListLabelProps}
        />,
      )}
    </div>
  )
}

LocusListLabels.propTypes = {
  locusLists: PropTypes.array.isRequired,
  compact: PropTypes.bool,
}

const GeneDetailSection = ({ details, compact, color, description, label, compactLabel }) => {
  if (!details) {
    return null
  }

  return compact ? (
    <div>
      <VerticalSpacer height={10} />
      <Label size="tiny" color={color} content={`${compactLabel || description}:`} />
      <HorizontalSpacer width={10} />
      {details}
    </div>
  ) : <GeneLabel color={color} label={label} popupHeader={description} popupContent={details} />
}

GeneDetailSection.propTypes = {
  details: PropTypes.node,
  compact: PropTypes.bool,
  color: PropTypes.string,
  description: PropTypes.string,
  label: PropTypes.string,
  compactLabel: PropTypes.string,
}

const VariantGene = ({ geneId, gene, project, variant, compact }) => {

  if (!gene) {
    return null
  }

  const geneSummary = (
    <div>
      <ShowGeneModal gene={gene} fontWeight="bold" fontSize={compact ? '1.2em' : '1.5em'} modalId={variant.variantId} />
      <HorizontalSpacer width={10} />
      {compact ? variant.transcripts[geneId] && variant.transcripts[geneId][0].consequence.replace(/_/g, ' ') :
      <GeneLinks>
        <a href={`http://gnomad-beta.broadinstitute.org/gene/${gene.geneSymbol}`} target="_blank">gnomAD</a>
        <HorizontalSpacer width={5} />|<HorizontalSpacer width={5} />
        <a href={`/project/${project.deprecatedProjectId}/gene/${gene.geneId}`} target="_blank">Gene Search</a><br />
      </GeneLinks>}
    </div>
  )

  const geneDetails =
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
      />
      <GeneDetailSection
        compact={compact}
        color="red"
        label="MISSENSE CONSTR"
        description="Missense Constraint"
        details={((gene.constraints.misZ && gene.constraints.misZ > 3) ||
          (gene.constraints.misZRank && gene.constraints.misZRank < CONSTRAINED_GENE_RANK_THRESHOLD)) &&
          `This gene ranks ${gene.constraints.misZRank} most constrained out of
          ${gene.constraints.totalGenes} genes under study in terms of missense constraint (z-score:
          ${gene.constraints.misZ.toPrecision(4)}). Missense contraint is a measure of the degree to which the number
          of missense variants found in this gene in ExAC v0.3 is higher or lower than expected according to the
          statistical model described in [K. Samocha 2014]. In general this metric is most useful for genes that act
          via a dominant mechanism, and where a large proportion of the protein is heavily functionally constrained.`}
      />
      <GeneDetailSection
        compact={compact}
        color="red"
        label="LOF CONSTR"
        description="Loss of Function Constraint"
        details={((gene.constraints.pli && gene.constraints.pli > 0.9) ||
          (gene.constraints.pliRank && gene.constraints.pliRank < CONSTRAINED_GENE_RANK_THRESHOLD)) &&
          `This gene ranks as ${gene.constraints.pliRank} most intolerant of LoF mutations out of
           ${gene.constraints.totalGenes} genes under study (pli: ${gene.constraints.pli.toPrecision(4)}).
           This metric is based on the amount of expected variation observed in the ExAC data and is a measure of how
           likely the gene is to be intolerant of loss-of-function mutations`}
      />
      <LocusListLabels locusLists={gene.locusLists} compact={compact} />
    </div>

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
  project: getProject(state),
  gene: getGenesById(state)[ownProps.geneId],
})

export default connect(mapStateToProps)(VariantGene)

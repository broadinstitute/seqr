import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Label, Popup, List } from 'semantic-ui-react'

import { getProject } from 'pages/Project/selectors'
import { getGenesById } from 'redux/selectors'
import { HorizontalSpacer } from '../../Spacers'
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

export const LocusListLabels = ({ locusLists }) =>
  <div>
    {locusLists.map(geneListName =>
      <GeneLabel
        key={geneListName}
        label={`${geneListName.substring(0, 10)}${geneListName.length > 10 ? ' ...' : ''}`}
        color="teal"
        popupHeader="Gene Lists"
        popupContent={locusLists.map(geneList => <div key={geneList}>{geneList}</div>)}
      />,
    )}
  </div>

LocusListLabels.propTypes = {
  locusLists: PropTypes.array.isRequired,
}

const VariantGene = ({ gene, project, variantId }) =>
  <div>
    <ShowGeneModal gene={gene} fontWeight="bold" fontSize="1.5em" modalId={variantId} />
    <HorizontalSpacer width={10} />
    <GeneLinks>
      <a href={`http://gnomad-beta.broadinstitute.org/gene/${gene.geneSymbol}`} target="_blank">gnomAD</a>
      {/* TODO have gene search link for new gene search including on search page */}
      {project &&
        <span>
          <HorizontalSpacer width={5} />|<HorizontalSpacer width={5} />
          <a href={`/project/${project.deprecatedProjectId}/gene/${gene.geneId}`} target="_blank">Gene Search</a><br />
        </span>
      }
    </GeneLinks>
    <div>
      {gene.omimPhenotypes.length > 0 &&
        <GeneLabel
          color="orange"
          label="IN OMIM"
          popupHeader="Disease Phenotypes"
          popupContent={
            <List>
              {gene.omimPhenotypes.map(phenotype =>
                <ListItemLink
                  key={phenotype.phenotypeDescription}
                  content={phenotype.phenotypeDescription}
                  target="_blank"
                  href={`https://www.omim.org/entry/${phenotype.phenotypeMimNumber}`}
                />,
              )}
            </List>
          }
        />
      }
      {((gene.constraints.misZ && gene.constraints.misZ > 3) ||
        (gene.constraints.misZRank && gene.constraints.misZRank < CONSTRAINED_GENE_RANK_THRESHOLD)) &&
        <GeneLabel
          color="red"
          label="MISSENSE CONSTR"
          popupHeader="Missense Constraint"
          popupContent={`This gene ranks ${gene.constraints.misZRank} most constrained out of
            ${gene.constraints.totalGenes} genes under study in terms of missense constraint (z-score:
            ${gene.constraints.misZ.toPrecision(4)}). Missense contraint is a measure of the degree to which the number
            of missense variants found in this gene in ExAC v0.3 is higher or lower than expected according to the
            statistical model described in [K. Samocha 2014]. In general this metric is most useful for genes that act
            via a dominant mechanism, and where a large proportion of the protein is heavily functionally constrained.`
          }
        />
      }
      {((gene.constraints.pli && gene.constraints.pli > 0.9) ||
        (gene.constraints.pliRank && gene.constraints.pliRank < CONSTRAINED_GENE_RANK_THRESHOLD)) &&
        <GeneLabel
          color="red"
          label="LOF CONSTR"
          popupHeader="Loss of Function Constraint"
          popupContent={`This gene ranks as ${gene.constraints.pliRank} most intolerant of LoF mutations out of
           ${gene.constraints.totalGenes} genes under study (pli: ${gene.constraints.pli.toPrecision(4)}).
           This metric is based on the amount of expected variation observed in the ExAC data and is a measure of how
           likely the gene is to be intolerant of loss-of-function mutations`
          }
        />
      }
    </div>
    <LocusListLabels locusLists={gene.locusLists} />
  </div>

VariantGene.propTypes = {
  gene: PropTypes.object,
  project: PropTypes.object,
  variantId: PropTypes.string.isRequired,
}

const mapStateToProps = (state, ownProps) => ({
  project: getProject(state),
  // TODo take out default when use new reference data
  gene: getGenesById(state)[ownProps.geneId] || { constraints: { missense: [], lof: {} }, phenotypeInfo: { mimPhenotypes: [], orphanetPhenotypes: [] }, locusLists: [] },
})

export default connect(mapStateToProps)(VariantGene)

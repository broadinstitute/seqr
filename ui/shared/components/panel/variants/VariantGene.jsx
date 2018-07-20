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
  size: 'small',
  color: props => props.color || 'grey',
  content: props => props.label,
})`
   margin: 0px 10px 10px 0px !important;
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
        popupContent={locusLists.map(geneList => <div>{geneList}</div>)}
      />,
    )}
  </div>

LocusListLabels.propTypes = {
  locusLists: PropTypes.array.isRequired,
}

const VariantGene = ({ gene, project }) =>
  <div>
    <ShowGeneModal gene={gene} fontWeight="bold" fontSize="1.5em" />
    <HorizontalSpacer width={10} />
    <GeneLinks>
      <a href={`http://gnomad-beta.broadinstitute.org/gene/${gene.symbol}`} target="_blank" rel="noopener noreferrer">gnomAD</a>
      <HorizontalSpacer width={5} />|<HorizontalSpacer width={5} />
      <a href={`/project/${project.deprecatedProjectId}/gene/${gene.geneId}`} target="_blank" rel="noopener noreferrer">Gene Search</a><br />
    </GeneLinks>
    <div>
      {gene.phenotypeInfo.mimPhenotypes.length > 0 &&
        <GeneLabel
          color="orange"
          label="IN OMIM"
          popupHeader="Disease Phenotypes"
          popupContent={
            <List>
              {gene.phenotypeInfo.mimPhenotypes.map(phenotype =>
                <ListItemLink
                  key={phenotype.description}
                  content={phenotype.description}
                  target="_blank"
                  href={`https://www.omim.org/entry/${phenotype.mim_id}`}
                />,
              )}
            </List>
          }
        />
      }
      {gene.phenotypeInfo.orphanetPhenotypes.length > 0 &&
        <GeneLabel
          color="orange"
          label="ORPHANET"
          popupHeader="Orphanet Phenotypes"
          popupContent={
            <List>
              {gene.phenotypeInfo.orphanetPhenotypes.map(phenotype =>
                <ListItemLink
                  key={phenotype.description}
                  content={phenotype.description}
                  target="_blank"
                  href={`http://www.orpha.net/consor/cgi-bin/Disease_Search.php?lng=EN&data_id=20460&Disease_Disease_Search_diseaseGroup=${phenotype.orphanet_id}`}
                />,
              )}
            </List>
          }
        />
      }
      {((gene.constraints.missense.constraint && gene.constraints.missense.constraint > 3) ||
        (gene.constraints.missense.rank && gene.constraints.missense.rank < CONSTRAINED_GENE_RANK_THRESHOLD)) &&
        <GeneLabel
          color="red"
          label="MISSENSE CONSTR"
          popupHeader="Missense Constraint"
          popupContent={`This gene ranks ${gene.constraints.missense.rank} most constrained out of
            ${gene.constraints.missense.totalGenes} genes under study in terms of missense constraint (z-score:
            ${gene.constraints.missense.constraint && gene.constraints.missense.constraint.toPrecision(4)}). Missense
            contraint is a measure of the degree to which the number of missense variants found in this gene in ExAC v0.3
            is higher or lower than expected according to the statistical model described in [K. Samocha 2014]. In general
            this metric is most useful for genes that act via a dominant mechanism, and where a large proportion of the
            protein is heavily functionally constrained.`
          }
        />
      }
      {((gene.constraints.lof.constraint && gene.constraints.lof.constraint > 0.9) ||
        (gene.constraints.lof.rank && gene.constraints.lof.rank < CONSTRAINED_GENE_RANK_THRESHOLD)) &&
        <GeneLabel
          color="red"
          label="LOF CONSTR"
          popupHeader="Loss of Function Constraint"
          popupContent={`This gene ranks as ${gene.constraints.lof.rank} most intolerant of LoF mutations out of
           ${gene.constraints.lof.totalGenes} genes under study (pLI: ${gene.constraints.lof.constraint &&
            gene.constraints.lof.constraint.toPrecision(4)}). This metric is based on the amount of expected
           variation observed in the ExAC data and is a measure of how likely the gene is to be intolerant of
           loss-of-function mutations`
          }
        />
      }
    </div>
    <LocusListLabels locusLists={gene.locusLists} />
  </div>

VariantGene.propTypes = {
  gene: PropTypes.object,
  project: PropTypes.object,
}

const mapStateToProps = (state, ownProps) => ({
  project: getProject(state),
  gene: getGenesById(state)[ownProps.geneId],
})

export default connect(mapStateToProps)(VariantGene)

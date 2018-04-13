import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Label, Popup } from 'semantic-ui-react'

import { getProject } from 'pages/Project/reducers'
import { HorizontalSpacer } from '../../Spacers'


const GeneLabel = ({ label, color, popupHeader, popupContent }) => {
  const content = <Label size="small" color={color || 'grey'} style={{ margin: '5px 10px 10px 0px' }}>{label}</Label>
  return popupContent ? <Popup header={popupHeader} trigger={content} content={popupContent} size="tiny" wide /> : content
}

GeneLabel.propTypes = {
  label: PropTypes.string.isRequired,
  color: PropTypes.string,
  popupHeader: PropTypes.string,
  popupContent: PropTypes.string,
}


const VariantGene = ({ gene, geneId, variant, project }) =>
  <div>
    {/*TODO gene modal*/}
    <b style={{ fontSize: '18px' }}><a>{gene.symbol || variant.extras.gene_names[geneId]}</a></b>
    <HorizontalSpacer width={10} />
    {gene.symbol &&
      <span>
        <a href={`http://www.gtexportal.org/home/gene/${gene.symbol}`} target="_blank">GTEx</a>
        <HorizontalSpacer width={5} />|<HorizontalSpacer width={5} />
      </span>
    }
    {gene.symbol &&
      <span>
        <a href={`http://gnomad-beta.broadinstitute.org/gene/${gene.symbol}`} target="_blank">gnomAD</a>
        <HorizontalSpacer width={5} />|<HorizontalSpacer width={5} />
      </span>
    }
    <a href={`/project/${project.deprecatedProjectId}/gene/${geneId}`} target="_blank">Gene Search</a><br />
    {gene.missense_constraint && gene.missense_constraint_rank[0] < 1000 &&
      <GeneLabel
        label="MISSENSE CONSTR"
        popupHeader="Missense Constraint"
        popupContent={`This gene ranks ${gene.missense_constraint_rank[0]} most constrained out of
          ${gene.missense_constraint_rank[1]} genes under study in terms of missense constraint (z-score:
          ${gene.missense_constraint.toPrecision(4)}). Missense contraint is a measure of the degree to which
          the number of missense variants found in this gene in ExAC v0.3 is higher or lower than expected
          according to the statistical model described in [K. Samocha 2014]. In general this metric is most
          useful for genes that act via a dominant mechanism, and where a large proportion of the protein
          is heavily functionally constrained.`
        }
      />
    }
    {gene.lof_constraint && gene.lof_constraint_rank[0] < 1000 &&
      <GeneLabel
        label="LOF CONSTR"
        popupHeader="Loss of Function Constraint"
        popupContent={`This gene ranks as ${gene.lof_constraint_rank[0]} most intolerant of LoF mutations out of
         ${gene.lof_constraint_rank[1]} genes under study. This metric is based on the amount of expected
         variation observed in the ExAC data and is a measure of how likely the gene is to be intolerant of l
         oss-of-function mutations`
        }
      />
    }
    {variant.extras.in_disease_gene_db && <GeneLabel color="orange" label="IN OMIM" />}
    {variant.extras.disease_genes && variant.extras.disease_genes.length > 0 &&
      variant.extras.disease_genes.map(geneListName =>
        <GeneLabel
          label={`${geneListName.substring(0, 10)}${geneListName.length > 6 ? ' ..' : ''}`}
          color="teal"
          popupHeader="Gene List"
          popupContent={geneListName}
        />,
    )}
  </div>

VariantGene.propTypes = {
  geneId: PropTypes.string.isRequired,
  gene: PropTypes.object,
  variant: PropTypes.object,
  project: PropTypes.object,
}

const mapStateToProps = state => ({
  project: getProject(state),
})

export default connect(mapStateToProps)(VariantGene)

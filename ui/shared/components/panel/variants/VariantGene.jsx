import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Label, Popup, Header } from 'semantic-ui-react'

import { getProject } from 'pages/Project/reducers'
import { HorizontalSpacer } from '../../Spacers'
import Modal from '../../modal/Modal'
import GeneDetail from '../genes/GeneDetail'


export const GeneLabel = ({ label, color, popupHeader, popupContent }) => {
  const content = <Label size="small" color={color || 'grey'} style={{ margin: '0px 10px 10px 0px' }}>{label}</Label>
  return popupContent ? <Popup header={popupHeader} trigger={content} content={popupContent} size="tiny" wide /> : content
}

GeneLabel.propTypes = {
  label: PropTypes.string.isRequired,
  color: PropTypes.string,
  popupHeader: PropTypes.string,
  popupContent: PropTypes.string,
}


const VariantGene = ({ gene, project }) =>
  <div>
    <Modal
      trigger={<Header size="large" style={{ display: 'inline-block' }}><a>{gene.symbol}</a></Header>}
      title={gene.symbol}
      modalName={`gene-${gene.geneId}`}
      size="fullscreen"
    >
      <GeneDetail geneId={gene.geneId} />
    </Modal>
    <HorizontalSpacer width={10} />
    <div style={{ display: 'inline-block' }}>
      <a href={`http://www.gtexportal.org/home/gene/${gene.symbol}`} target="_blank">GTEx</a>
      <HorizontalSpacer width={5} />|<HorizontalSpacer width={5} />
      <a href={`http://gnomad-beta.broadinstitute.org/gene/${gene.symbol}`} target="_blank">gnomAD</a>
      <HorizontalSpacer width={5} />|<HorizontalSpacer width={5} />
      <a href={`/project/${project.deprecatedProjectId}/gene/${gene.geneId}`} target="_blank">Gene Search</a><br />
    </div>
    {gene.constraints.missense.constraint && gene.constraints.missense.rank < 1000 &&
      <GeneLabel
        label="MISSENSE CONSTR"
        popupHeader="Missense Constraint"
        popupContent={`This gene ranks ${gene.constraints.missense.rank} most constrained out of
          ${gene.constraints.missense.totalGenes} genes under study in terms of missense constraint (z-score:
          ${gene.constraints.missense.constraint.toPrecision(4)}). Missense contraint is a measure of the degree to
          which the number of missense variants found in this gene in ExAC v0.3 is higher or lower than expected
          according to the statistical model described in [K. Samocha 2014]. In general this metric is most
          useful for genes that act via a dominant mechanism, and where a large proportion of the protein
          is heavily functionally constrained.`
        }
      />
    }
    {gene.constraints.lof.constraint && gene.constraints.lof.rank < 1000 &&
      <GeneLabel
        label="LOF CONSTR"
        popupHeader="Loss of Function Constraint"
        popupContent={`This gene ranks as ${gene.constraints.lof.rank} most intolerant of LoF mutations out of
         ${gene.constraints.lof.totalGenes} genes under study. This metric is based on the amount of expected
         variation observed in the ExAC data and is a measure of how likely the gene is to be intolerant of l
         oss-of-function mutations`
        }
      />
    }
  </div>

VariantGene.propTypes = {
  gene: PropTypes.object,
  project: PropTypes.object,
}

const mapStateToProps = state => ({
  project: getProject(state),
})

export default connect(mapStateToProps)(VariantGene)

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Label, Popup, Header } from 'semantic-ui-react'

import { getProject } from 'pages/Project/selectors'
import { HorizontalSpacer } from '../../Spacers'
import Modal from '../../modal/Modal'
import GeneDetail from '../genes/GeneDetail'

const CONSTRAINED_GENE_RANK_THRESHOLD = 1000

const GeneLabelContent = styled(Label).attrs({
  size: 'small',
  color: props => props.color || 'grey',
  content: props => props.label,
})`
   margin: 0px 10px 10px 0px;
`

const InlineHeader = styled(Header)`
  display: inline-block;
`

const GeneLabel = ({ popupHeader, popupContent, ...labelProps }) => {
  const content = <GeneLabelContent {...labelProps} />
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
      trigger={<InlineHeader size="large"><a>{gene.symbol}</a></InlineHeader>}
      title={gene.symbol}
      modalName={`gene-${gene.geneId}`}
      size="fullscreen"
    >
      <GeneDetail geneId={gene.geneId} />
    </Modal>
    <HorizontalSpacer width={10} />
    <div style={{ display: 'inline-block' }}>
      <a href={`http://gnomad-beta.broadinstitute.org/gene/${gene.symbol}`} target="_blank">gnomAD</a>
      <HorizontalSpacer width={5} />|<HorizontalSpacer width={5} />
      <a href={`/project/${project.deprecatedProjectId}/gene/${gene.geneId}`} target="_blank">Gene Search</a><br />
    </div>
    <div>
      {gene.inDiseaseDb && <GeneLabel color="orange" label="IN OMIM" />}
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
    <div>
      {gene.diseaseGeneLists.map(geneListName =>
        <GeneLabel
          key={geneListName}
          label={`${geneListName.substring(0, 10)}${geneListName.length > 6 ? ' ..' : ''}`}
          color="teal"
          popupHeader="Gene Lists"
          popupContent={gene.diseaseGeneLists.join(', ')}
        />,
      )}
    </div>
  </div>

VariantGene.propTypes = {
  gene: PropTypes.object,
  project: PropTypes.object,
}

const mapStateToProps = state => ({
  project: getProject(state),
})

export default connect(mapStateToProps)(VariantGene)

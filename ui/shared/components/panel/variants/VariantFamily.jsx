import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getProject, getFamiliesByGuid, getIndividualsByGuid } from 'redux/rootReducer'
import PedigreeIcon from '../../icons/PedigreeIcon'
import { HorizontalSpacer } from '../../Spacers'

const Allele = ({ allele, variant }) => {
  let alleleText = allele.substring(0, 3)
  if (allele.length > 3) {
    alleleText += '..'
  }
  return allele !== variant.ref ? <b><i>{alleleText}</i></b> : <span>{alleleText}</span>
}

Allele.propTypes = {
  allele: PropTypes.string,
  variant: PropTypes.object,
}

//TODO add gentype.filter to hover

const VariantFamily = ({ variant, project, family, individualsByGuid }) =>
  <span>
    <span>
      <b>Family<HorizontalSpacer width={5} /></b>
      <a href={`/project/${project.deprecatedProjectId}/family/${family.familyId}`}>
        {family.displayName}
      </a>
    </span>
    {family.individualGuids.map((individualGuid) => {
      const individual = individualsByGuid[individualGuid]
      const genotype = variant.genotypes[individual.individualId]
      // <Allele allele={genotype.alleles[0]} variant={variant} /> / <Allele allele={genotype.alleles[1]} variant={variant} />
      return (
        <span key={individualGuid}>
          <HorizontalSpacer width={30} />
          <PedigreeIcon sex={individual.sex} affected={individual.affected} />
          <b>{individual.displayName || individual.individualId}:</b>
          <HorizontalSpacer width={5} />
          {genotype && genotype.alleles.length === 2 && genotype.num_alt !== -1 ?
            <span>
              <Allele allele={genotype.alleles[0]} variant={variant} />/<Allele allele={genotype.alleles[1]} variant={variant} />
            </span>
            : <b>NO CALL</b>
          }
          {genotype && genotype.gq && <span><HorizontalSpacer width={5} />({genotype.gq})</span>}
        </span>
      )
    })}
  </span>

VariantFamily.propTypes = {
  variant: PropTypes.object,
  project: PropTypes.object,
  family: PropTypes.object,
  individualsByGuid: PropTypes.object,
}

const mapStateToProps = (state, ownProps) => ({
  project: getProject(state),
  family: getFamiliesByGuid(state)[ownProps.variant.familyGuid],
  individualsByGuid: getIndividualsByGuid(state),
})

export default connect(mapStateToProps)(VariantFamily)

import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Popup } from 'semantic-ui-react'

import { getFamiliesByGuid, getIndividualsByGuid } from 'redux/rootReducer'
import { getProject } from 'pages/Project/reducers'
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

      const qualityDetails = genotype ? [
        // TODO confirm no longer need Raw Alt. Alleles
        // { title: 'Raw Alt. Alleles', value: genotype.extras.orig_alt_alleles.join().replace(/,/g, ", "), shouldShow: true },
        { title: 'Allelic Depth', value: genotype.extras.ad },
        { title: 'Read Depth', value: genotype.extras.dp },
        { title: 'Genotype Quality', value: genotype.gq },
        { title: 'Filter', value: genotype.filter, shouldHide: genotype.filter === 'pass' },
        { title: 'Phred Likelihoods', value: genotype.extras.pl },
        { title: 'Allelic Balance', value: genotype.ab && genotype.ab.toPrecision(2) },
      ] : []

      const variantIndividual =
        <span key={individualGuid}>
          <HorizontalSpacer width={30} />
          <PedigreeIcon sex={individual.sex} affected={individual.affected} />
          <b>{individual.displayName || individual.individualId}:</b>
          <HorizontalSpacer width={5} />
          {genotype && genotype.alleles.length === 2 && genotype.num_alt !== -1 ?
            <span>
              <Allele allele={genotype.alleles[0]} variant={variant} />/<Allele allele={genotype.alleles[1]} variant={variant} />
            </span>
            : <b>NO CALL</b>}
          {genotype && genotype.gq && <span><HorizontalSpacer width={5} />({genotype.gq})</span>}
        </span>

      return genotype && genotype.alleles.length > 0 ?
        <Popup
          key={individualGuid}
          position="top center"
          flowing
          trigger={variantIndividual}
          content={
            qualityDetails.map(({ shouldHide, title, value }) => {
              return value && !shouldHide ?
                <span key={title}>{title}:<HorizontalSpacer width={10} /><b>{value}</b><br /></span> : null
            })
          }
        />
        : variantIndividual
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

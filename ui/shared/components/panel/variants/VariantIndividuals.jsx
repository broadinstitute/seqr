import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Popup, Icon } from 'semantic-ui-react'

import { getSortedIndividualsByFamily } from 'redux/selectors'
import ShowReadsButton from '../../buttons/ShowReadsButton'
import PedigreeIcon from '../../icons/PedigreeIcon'
import { HorizontalSpacer, VerticalSpacer } from '../../Spacers'
import PhenotipsDataPanel, { hasPhenotipsDetails } from '../PhenotipsDataPanel'


const IndividualsContainer = styled.div`
  display: inline-block;
  padding: 0 10px;
  border-left: 1px solid grey;
  border-right: .5px solid grey;
  margin-left: -1px;
  margin-bottom: 5px;
  border-left: none;
  
  &:first-child {
    padding-left 0;
    margin-left: 0;
    border-left: none;
  }
  
  &:last-child {
    border-right: none;
  }
  
`

const IndividualCell = styled.div`
  display: inline-block;
  vertical-align: top;
  text-align: center;
  padding-right: 20px;
  max-width: ${props => 100 / Math.min(props.numIndividuals, 4)}%;
  overflow: hidden;
  text-overflow: ellipsis;
  
  small {
    text-overflow: ellipsis;
  }
  
  .ui.header {
    padding-top: 3px;
  }
`

const AlleleContainer = styled.span`
  color: black;
  font-size: 1.2em;
`

const PAR_REGIONS = {
  37: {
    X: [[60001, 2699521], [154931044, 155260561]],
    Y: [[10001, 2649521], [59034050, 59363567]],
  },
  38: {
    X: [[10001, 2781480], [155701383, 156030896]],
    Y: [[10001, 2781480], [56887903, 57217416]],
  },
}

const isHemiXVariant = (variant, individual) =>
  individual.sex === 'M' && (variant.chrom === 'X' || variant.chrom === 'Y') &&
  PAR_REGIONS[variant.genomeVersion][variant.chrom].every(region => variant.pos < region[0] || variant.pos > region[1])

const missingParentVariant = variant => (parentGuid) => {
  const parentGenotype = variant.genotypes[parentGuid] || {}
  return parentGenotype.numAlt === 0 && parentGenotype.affected !== 'A'
}

const isHemiUPDVariant = (numAlt, variant, individual) =>
  numAlt === 2 && [individual.maternalGuid, individual.paternalGuid].some(missingParentVariant(variant))

const Allele = React.memo(({ isAlt, variant }) => {
  const allele = isAlt ? variant.alt : variant.ref
  let alleleText = allele.substring(0, 3)
  if (allele.length > 3) {
    alleleText += '...'
  }

  return isAlt ? <b><i>{alleleText}</i></b> : alleleText
})

Allele.propTypes = {
  isAlt: PropTypes.bool,
  variant: PropTypes.object,
}

export const Alleles = React.memo(({ numAlt, cn, variant, isHemiX, warning }) =>
  <AlleleContainer>
    {warning &&
      <Popup
        flowing
        trigger={<Icon name="warning sign" color="yellow" />}
        content={<div><b>Warning:</b> {warning}</div>}
      />
    }
    {numAlt >= 0 ?
      <span>
        <Allele isAlt={numAlt > (isHemiX ? 0 : 1)} variant={variant} />/{isHemiX ? '-' : <Allele isAlt={numAlt > 0} variant={variant} />}
      </span> :
      <span>CN: {cn === (isHemiX ? 1 : 2) ? cn : <b><i>{cn}</i></b>}</span>
    }
  </AlleleContainer>,
)

Alleles.propTypes = {
  numAlt: PropTypes.number,
  cn: PropTypes.number,
  variant: PropTypes.object,
  warning: PropTypes.string,
  isHemiX: PropTypes.bool,
}


const Genotype = React.memo(({ variant, individual, isCompoundHet }) => {
  if (!variant.genotypes) {
    return null
  }
  const genotype = variant.genotypes[individual.individualGuid]
  if (!genotype) {
    return null
  }

  const qualityDetails = [
    {
      title: 'Raw Alt. Alleles',
      value: (variant.originalAltAlleles || []).join(', '),
      shouldHide: (variant.originalAltAlleles || []).length < 1 ||
      (variant.originalAltAlleles.length === 1 && variant.originalAltAlleles[0] === variant.alt),
    },
    { title: 'Allelic Depth', value: genotype.ad },
    { title: 'Read Depth', value: genotype.dp },
    { title: 'Genotype Quality', value: genotype.gq },
    { title: 'Allelic Balance', value: genotype.ab && genotype.ab.toPrecision(2) },
    { title: 'Filter', value: variant.genotypeFilters, shouldHide: (variant.genotypeFilters || []).length < 1 },
    { title: 'Phred Likelihoods', value: genotype.pl },
    { title: 'Quality Score', value: genotype.qs },
    { title: 'Start', value: genotype.start },
    { title: 'End', value: genotype.end },
  ]
  const isHemiX = isHemiXVariant(variant, individual)

  let warning
  if (genotype.defragged) {
    warning = 'Defragged'
  } else if (!isHemiX && isHemiUPDVariant(genotype.numAlt, variant, individual)) {
    warning = 'Potential UPD/ Hemizygosity'
  } else if (isCompoundHet && [individual.maternalGuid, individual.paternalGuid].every(missingParentVariant(variant))) {
    warning = 'Variant absent in parents'
  }

  return (
    (genotype.numAlt >= 0 || (variant.svType && genotype.cn >= 0)) ?
      <Popup
        position="top center"
        flowing
        trigger={
          <span>
            <Alleles cn={genotype.cn} numAlt={genotype.numAlt} variant={variant} isHemiX={isHemiX} warning={warning} />
            <VerticalSpacer width={5} />
            {genotype.gq || genotype.qs || '-'}{genotype.numAlt >= 0 && `, ${genotype.ab ? genotype.ab.toPrecision(2) : '-'}`}
            {variant.genotypeFilters && <small><br />{variant.genotypeFilters}</small>}
          </span>
        }
        content={
          qualityDetails.map(({ shouldHide, title, value }) => {
            return value && !shouldHide ?
              <div key={title}>{title}:<HorizontalSpacer width={10} /><b>{value}</b></div> : null
          })
        }
      />
      : <b>NO CALL</b>
  )
})

Genotype.propTypes = {
  variant: PropTypes.object,
  individual: PropTypes.object,
  isCompoundHet: PropTypes.bool,
}


const VariantIndividuals = React.memo(({ variant, individuals, familyGuid, isCompoundHet }) => (
  <IndividualsContainer>
    {(individuals || []).map(individual =>
      <IndividualCell key={individual.individualGuid} numIndividuals={individuals.length}>
        <PedigreeIcon
          sex={individual.sex}
          affected={individual.affected}
          label={<small>{individual.displayName}</small>}
          popupHeader={individual.displayName}
          popupContent={
            hasPhenotipsDetails(individual.phenotipsData) ?
              <PhenotipsDataPanel
                individual={individual}
                showDetails
                showEditPhenotipsLink={false}
                showViewPhenotipsLink={false}
              /> : null
          }
        />
        <br />
        <Genotype variant={variant} individual={individual} isCompoundHet={isCompoundHet} />
      </IndividualCell>,
    )}
    <ShowReadsButton familyGuid={familyGuid} igvId={variant.variantId} />
  </IndividualsContainer>
))

VariantIndividuals.propTypes = {
  familyGuid: PropTypes.string,
  variant: PropTypes.object,
  individuals: PropTypes.array,
  isCompoundHet: PropTypes.bool,
}

const mapStateToProps = (state, ownProps) => ({
  individuals: getSortedIndividualsByFamily(state)[ownProps.familyGuid],
})

export default connect(mapStateToProps)(VariantIndividuals)

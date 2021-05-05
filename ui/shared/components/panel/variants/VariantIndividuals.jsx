import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Popup, Icon, Header } from 'semantic-ui-react'

import { getSortedIndividualsByFamily } from 'redux/selectors'
import PedigreeIcon from '../../icons/PedigreeIcon'
import { HorizontalSpacer, VerticalSpacer } from '../../Spacers'
import HpoPanel from '../HpoPanel'


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

const AlleleContainer = styled(Header).attrs({ size: 'medium' })`
  &.ui.header {
    font-weight: 300;
    white-space: nowrap;
    .content {
      width: 100%;
    }
    &.ui.header>.icon {
      font-size: 1em;
     }
  }
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

const Allele = styled.div.attrs(({ isAlt, variant }) => ({ children: isAlt ? variant.alt : variant.ref }))`
  display: inline-block;
  max-width: 50px;
  width: 40%;
  height: 1em;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: ${props => props.textAlign};
  ${props => (props.isAlt ? `
    font-style: italic;
    font-weight: 400;` : '')}
`

Allele.propTypes = {
  isAlt: PropTypes.bool,
  variant: PropTypes.object,
}

export const Alleles = React.memo(({ genotype, variant, isHemiX, warning }) =>
  <AlleleContainer>
    {warning &&
      <Popup
        flowing
        trigger={<Icon name="warning sign" color="yellow" />}
        content={<div><b>Warning:</b> {warning}</div>}
      />
    }
    {genotype.numAlt >= 0 ?
      <Header.Content>
        <Allele isAlt={genotype.numAlt > (isHemiX ? 0 : 1)} variant={variant} textAlign="right" />
        /{isHemiX ? '-' : <Allele isAlt={genotype.numAlt > 0} variant={variant} textAlign="left" />}
      </Header.Content> :
      <Header.Content>CN: {genotype.cn === (isHemiX ? 1 : 2) ? genotype.cn : <b><i>{genotype.cn}</i></b>}</Header.Content>
    }
  </AlleleContainer>,
)

Alleles.propTypes = {
  genotype: PropTypes.object,
  variant: PropTypes.object,
  warning: PropTypes.string,
  isHemiX: PropTypes.bool,
}

const GENOTYPE_DETAILS = [
  { title: 'Sample Type', field: 'sampleType' },
  {
    title: 'Raw Alt. Alleles',
    variantField: 'originalAltAlleles',
    format: val => (val || []).join(', '),
    shouldHide: (val, variant) => (val || []).length < 1 || ((val || []).length === 1 && val[0] === variant.alt),
  },
  { title: 'Allelic Depth', field: 'ad' },
  { title: 'Read Depth', field: 'dp' },
  { title: 'Genotype Quality', field: 'gq' },
  { title: 'Allelic Balance', field: 'ab', format: val => val && val.toPrecision(2) },
  { title: 'Filter', variantField: 'genotypeFilters', shouldHide: val => (val || []).length < 1 },
  { title: 'Phred Likelihoods', field: 'pl' },
  { title: 'Quality Score', field: 'qs' },
  { title: 'Start', field: 'start' },
  { title: 'End', field: 'end' },
]

const genotypeDetails = (genotype, variant) =>
  GENOTYPE_DETAILS.map(({ shouldHide, title, field, variantField, format }) => {
    const value = field ? genotype[field] : variant[variantField]
    return value && !(shouldHide && shouldHide(value, variant)) ?
      <div key={title}>
        {title}:<HorizontalSpacer width={10} /><b>{format ? format(value) : value}</b>
      </div> : null
  }).filter(val => val)

const Genotype = React.memo(({ variant, individual, isCompoundHet }) => {
  if (!variant.genotypes) {
    return null
  }
  const genotype = variant.genotypes[individual.individualGuid]
  if (!genotype) {
    return null
  }

  if (genotype.numAlt < 0 || (variant.svType && genotype.cn < 0)) {
    return <b>NO CALL</b>
  }

  const isHemiX = isHemiXVariant(variant, individual)

  let warning
  if (genotype.defragged) {
    warning = 'Defragged'
  } else if (!isHemiX && isHemiUPDVariant(genotype.numAlt, variant, individual)) {
    warning = 'Potential UPD/ Hemizygosity'
  } else if (isCompoundHet && [individual.maternalGuid, individual.paternalGuid].every(missingParentVariant(variant))) {
    warning = 'Variant absent in parents'
  }

  const hasConflictingNumAlt = genotype.otherSample && genotype.otherSample.numAlt !== genotype.numAlt
  const details = genotypeDetails(genotype, variant)

  const content = (
    <span>
      {genotype.otherSample && <Popup
        flowing
        header="Additional Sample Type"
        trigger={<Icon name="plus circle" color={hasConflictingNumAlt ? 'red' : 'green'} />}
        content={
          <div>
            {hasConflictingNumAlt &&
              <div>
                <VerticalSpacer height={5} />
                <Alleles genotype={genotype.otherSample} variant={variant} isHemiX={isHemiX} />
                <VerticalSpacer height={5} />
              </div>
            }
            {genotypeDetails(genotype.otherSample, variant)}
          </div>
        }
      />}
      <Alleles genotype={genotype} variant={variant} isHemiX={isHemiX} warning={warning} />
      <VerticalSpacer height={2} />
      {genotype.gq || genotype.qs || '-'}{genotype.numAlt >= 0 && `, ${genotype.ab ? genotype.ab.toPrecision(2) : '-'}`}
      {variant.genotypeFilters && <small><br />{variant.genotypeFilters}</small>}
    </span>
  )

  return details.length ? <Popup position="top center" flowing trigger={content} content={details} /> : content
})

Genotype.propTypes = {
  variant: PropTypes.object,
  individual: PropTypes.object,
  isCompoundHet: PropTypes.bool,
}


const BaseVariantIndividuals = React.memo(({ variant, individuals, isCompoundHet }) => (
  <IndividualsContainer>
    {(individuals || []).map(individual =>
      <IndividualCell key={individual.individualGuid} numIndividuals={individuals.length}>
        <PedigreeIcon
          sex={individual.sex}
          affected={individual.affected}
          label={<small>{individual.displayName}</small>}
          popupHeader={individual.displayName}
          popupContent={
            individual.features ? <HpoPanel individual={individual} /> : null
          }
        />
        <br />
        <Genotype variant={variant} individual={individual} isCompoundHet={isCompoundHet} />
      </IndividualCell>,
    )}
  </IndividualsContainer>
))

BaseVariantIndividuals.propTypes = {
  variant: PropTypes.object,
  individuals: PropTypes.array,
  isCompoundHet: PropTypes.bool,
}

const mapStateToProps = (state, ownProps) => ({
  individuals: getSortedIndividualsByFamily(state)[ownProps.familyGuid],
})

const FamilyVariantIndividuals = connect(mapStateToProps)(BaseVariantIndividuals)

const VariantIndividuals = React.memo(({ variant, isCompoundHet }) =>
  <span>
    {variant.familyGuids.map(familyGuid =>
      <FamilyVariantIndividuals key={familyGuid} familyGuid={familyGuid} variant={variant} isCompoundHet={isCompoundHet} />,
    )}
  </span>,
)


VariantIndividuals.propTypes = {
  variant: PropTypes.object,
  isCompoundHet: PropTypes.bool,
}

export default VariantIndividuals

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Popup, Icon, Header, Divider, Label } from 'semantic-ui-react'

import { getSortedIndividualsByFamily, getGenesById } from 'redux/selectors'
import PedigreeIcon from '../../icons/PedigreeIcon'
import { VerticalSpacer } from '../../Spacers'
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
    margin-bottom: 3px;
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

const isHemiXVariant =
  (variant, individual) => individual.sex === 'M' && (variant.chrom === 'X' || variant.chrom === 'Y') &&
  PAR_REGIONS[variant.genomeVersion][variant.chrom].every(region => variant.pos < region[0] || variant.pos > region[1])

const missingParentVariant = variant => (parentGuid) => {
  const parentGenotype = variant.genotypes[parentGuid] || {}
  return parentGenotype.numAlt === 0 && parentGenotype.affected !== 'A'
}

const isHemiUPDVariant = (numAlt, variant, individual) => (
  numAlt === 2 && [individual.maternalGuid, individual.paternalGuid].some(missingParentVariant(variant)))

const isCalled = val => Number.isInteger(val) && val >= 0

const getGentoypeCnWarning = (genotype, svType, isHemiX) => {
  const refCn = isHemiX ? 1 : 2
  const hasGentotype = isCalled(genotype.numAlt)

  if ((svType === 'DUP' && genotype.cn < refCn) || (svType === 'DEL' && genotype.cn > refCn)) {
    return `Copy Number does not match Call Type. Copy number calling may be unreliable for small events${hasGentotype ? ', however genotype call is likely accurate' : ''}`
  }

  if (hasGentotype && (
    (genotype.numAlt === 0 && genotype.cn !== refCn) || (genotype.numAlt > 0 && genotype.cn === refCn))) {
    return 'Copy number does not match genotype. Copy number calling may be unreliable for small events, however genotype call is likely accurate'
  }

  return null
}

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

const copyNumberGenotype = (cn, isHemiX) => (
  <span>
    CN: &nbsp;
    {cn !== (isHemiX ? 1 : 2) ? <b><i>{cn}</i></b> : cn}
  </span>
)

const svGenotype = (genotype, isHemiX) => {
  const cnDisplay = isCalled(genotype.cn) && copyNumberGenotype(genotype.cn, isHemiX)
  if (!isCalled(genotype.numAlt)) {
    return cnDisplay
  }
  return (
    <span>
      {/* eslint-disable-next-line react/jsx-one-expression-per-line */}
      {isHemiX || genotype.numAlt < 2 ? 'ref' : <b><i>alt</i></b>}/{genotype.numAlt > 0 ? <b><i>alt</i></b> : 'ref'}
      {cnDisplay && <br />}
      {cnDisplay}
    </span>
  )
}

export const Alleles = React.memo(({ genotype, variant, isHemiX, warning }) => (
  <AlleleContainer>
    {warning && (
      <Popup
        wide
        trigger={<Icon name="warning sign" color="yellow" />}
        content={
          <div>
            <b>Warning: </b>
            {warning}
          </div>
        }
      />
    )}
    {variant.svType ? (
      <Header.Content>
        {svGenotype(genotype, isHemiX)}
      </Header.Content>
    ) : (
      <Header.Content>
        <Allele isAlt={genotype.numAlt > (isHemiX ? 0 : 1)} variant={variant} textAlign="right" />
        /
        {isHemiX ? '-' : <Allele isAlt={genotype.numAlt > 0} variant={variant} textAlign="left" />}
      </Header.Content>
    )}
  </AlleleContainer>
))

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
]

const SV_GENOTYPE_DETAILS = [
  { title: 'Start', field: 'start' },
  { title: 'End', field: 'end' },
  { title: '# Exons', field: 'numExon' },
  {
    title: 'Genes',
    field: 'geneIds',
    format: (val, genesById) => val.map(geneId => (genesById[geneId] || {}).geneSymbol || geneId).join(', '),
  },
]

const formattedGenotypeDetails = (details, genotype, variant, genesById) => details.map(
  ({ shouldHide, title, field, variantField, format }) => {
    const value = field ? genotype[field] : variant[variantField]
    return value && !(shouldHide && shouldHide(value, variant)) ? (
      <div key={title}>
        {`${title}:  `}
        <b>{format ? format(value, genesById) : value}</b>
      </div>
    ) : null
  },
).filter(val => val)

const genotypeDetails = (genotype, variant, genesById) => {
  const details = formattedGenotypeDetails(GENOTYPE_DETAILS, genotype, variant)
  const svDetails = formattedGenotypeDetails(SV_GENOTYPE_DETAILS, genotype, variant, genesById)
  if (svDetails.length < 1) {
    return details
  }
  return [
    ...details,
    <VerticalSpacer height={10} key="spacer" />,
    <Divider horizontal fitted key="divider">Sample SV</Divider>,
    ...svDetails,
  ]
}

const Genotype = React.memo(({ variant, individual, isCompoundHet, genesById }) => {
  if (!variant.genotypes) {
    return null
  }
  const genotype = variant.genotypes[individual.individualGuid]
  if (!genotype) {
    return null
  }

  const hasCnCall = isCalled(genotype.cn)
  if (!hasCnCall && !isCalled(genotype.numAlt)) {
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

  if (hasCnCall) {
    const cnWarning = getGentoypeCnWarning(genotype, variant.svType, isHemiX)
    if (cnWarning) {
      warning = warning ? `${warning}. ${cnWarning}` : cnWarning
    }
  }

  let previousCall
  if (genotype.newCall) {
    previousCall = { content: 'New Call', hover: 'No overlap in previous callset', color: 'green' }
  } else if (genotype.prevCall) {
    previousCall = { content: 'Identical Call', hover: 'Identical call in previous callset', color: 'blue' }
  } else if (genotype.prevOverlap) {
    previousCall = { content: 'Overlapping Call', hover: 'Overlapping call in previous callset', color: 'teal' }
  }

  const hasConflictingNumAlt = genotype.otherSample && genotype.otherSample.numAlt !== genotype.numAlt
  const details = genotypeDetails(genotype, variant, genesById)

  const content = (
    <span>
      {genotype.otherSample && (
        <Popup
          header="Additional Sample Type"
          trigger={<Icon name="plus circle" color={hasConflictingNumAlt ? 'red' : 'green'} />}
          content={
            <div>
              {hasConflictingNumAlt && (
                <div>
                  <VerticalSpacer height={5} />
                  <Alleles genotype={genotype.otherSample} variant={variant} isHemiX={isHemiX} />
                  <VerticalSpacer height={5} />
                </div>
              )}
              {genotypeDetails(genotype.otherSample, variant, genesById)}
            </div>
          }
        />
      )}
      <Alleles genotype={genotype} variant={variant} isHemiX={isHemiX} warning={warning} />
      {previousCall && (
        <Popup
          content={previousCall.hover}
          trigger={<Label horizontal size="mini" content={previousCall.content} color={previousCall.color} />}
        />
      )}
      {`${genotype.gq || genotype.qs || '-'}${variant.svType ? '' : genotype.numAlt >= 0 && `, ${genotype.ab ? genotype.ab.toPrecision(2) : '-'}`}`}
      {variant.genotypeFilters && (
        <small>
          <br />
          {variant.genotypeFilters}
        </small>
      )}
    </span>
  )

  return details.length ? <Popup position="top center" trigger={content} content={details} /> : content
})

Genotype.propTypes = {
  variant: PropTypes.object,
  individual: PropTypes.object,
  isCompoundHet: PropTypes.bool,
  genesById: PropTypes.object,
}

const BaseVariantIndividuals = React.memo(({ variant, individuals, isCompoundHet, genesById }) => (
  <IndividualsContainer>
    {(individuals || []).map(individual => (
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
        <Genotype variant={variant} individual={individual} isCompoundHet={isCompoundHet} genesById={genesById} />
      </IndividualCell>
    ))}
  </IndividualsContainer>
))

BaseVariantIndividuals.propTypes = {
  variant: PropTypes.object,
  individuals: PropTypes.arrayOf(PropTypes.object),
  isCompoundHet: PropTypes.bool,
  genesById: PropTypes.object,
}

const mapStateToProps = (state, ownProps) => ({
  individuals: getSortedIndividualsByFamily(state)[ownProps.familyGuid],
  genesById: getGenesById(state),
})

const FamilyVariantIndividuals = connect(mapStateToProps)(BaseVariantIndividuals)

const VariantIndividuals = React.memo(({ variant, isCompoundHet }) => (
  <span>
    {variant.familyGuids.map(familyGuid => (
      <FamilyVariantIndividuals
        key={familyGuid}
        familyGuid={familyGuid}
        variant={variant}
        isCompoundHet={isCompoundHet}
      />
    ))}
  </span>
))

VariantIndividuals.propTypes = {
  variant: PropTypes.object,
  isCompoundHet: PropTypes.bool,
}

export default VariantIndividuals

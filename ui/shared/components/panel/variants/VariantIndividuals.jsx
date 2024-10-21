import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Popup, Icon, Header, Divider, Label } from 'semantic-ui-react'

import { getSortedIndividualsByFamily, getGenesById } from 'redux/selectors'
import {
  INDIVIDUAL_FIELD_FEATURES,
  INDIVIDUAL_FIELD_FILTER_FLAGS,
  INDIVIDUAL_FIELD_POP_FILTERS,
  INDIVIDUAL_FIELD_SV_FLAGS,
  INDIVIDUAL_FIELD_LOOKUP,
  SAMPLE_TYPE_EXOME,
  SAMPLE_TYPE_GENOME,
} from 'shared/utils/constants'
import BaseFieldView from '../view-fields/BaseFieldView'
import PedigreeIcon from '../../icons/PedigreeIcon'
import { VerticalSpacer } from '../../Spacers'
import { ColoredDiv } from '../../StyledComponents'

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

const WarningIcon = props => <Icon name="warning sign" color="yellow" {...props} />

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

const SAMPLE_TYPE_DISPLAY_ORDER = [SAMPLE_TYPE_GENOME, SAMPLE_TYPE_EXOME]

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

const copyNumberGenotype = (cn, newline, isHemiX) => (isCalled(cn) && (
  <span>
    {newline && <br />}
    CN: &nbsp;
    {cn !== (isHemiX ? 1 : 2) ? <b><i>{cn}</i></b> : cn}
  </span>
))

const svNumAltGenotype = (numAlt, isHemiX) => (
  <span>
    {isHemiX || numAlt < 2 ? 'ref' : <b><i>alt</i></b>}
    /
    {numAlt > 0 ? <b><i>alt</i></b> : 'ref'}
  </span>
)

const svGenotype = (genotype, isHemiX) => {
  if (!isCalled(genotype.numAlt)) {
    return copyNumberGenotype(genotype.cn, false, isHemiX)
  }
  return (
    <span>
      {svNumAltGenotype(genotype.numAlt, isHemiX)}
      {copyNumberGenotype(genotype.cn, true, isHemiX)}
    </span>
  )
}

const AllelesHeader = ({ genotype, variant, isHemiX }) => (
  <Header.Content>
    <Allele isAlt={genotype.numAlt > (isHemiX ? 0 : 1)} variant={variant} textAlign="right" />
    /
    {isHemiX ? '-' : <Allele isAlt={genotype.numAlt > 0} variant={variant} textAlign="left" />}
    {genotype.mitoCn && (copyNumberGenotype(genotype.mitoCn, true))}
  </Header.Content>
)

AllelesHeader.propTypes = {
  genotype: PropTypes.object,
  variant: PropTypes.object,
  isHemiX: PropTypes.bool,
}

export const Alleles = React.memo(({ genotype, variant, isHemiX, warning }) => (
  <AlleleContainer>
    {warning && (
      <Popup
        wide
        trigger={<WarningIcon />}
        content={warning}
      />
    )}
    {variant.svType ? (
      <Header.Content>
        {svGenotype(genotype, isHemiX)}
      </Header.Content>
    ) : <AllelesHeader genotype={genotype} variant={variant} isHemiX={isHemiX} />}
  </AlleleContainer>
))

Alleles.propTypes = {
  genotype: PropTypes.object,
  variant: PropTypes.object,
  warning: PropTypes.node,
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
  { title: 'Filter', field: 'filters', variantField: 'genotypeFilters', shouldHide: val => (val || []).length < 1 },
  { title: 'Phred Likelihoods', field: 'pl' },
  { title: 'Quality Score', field: 'qs' },
  {
    title: 'Mitochondrial Copy Number',
    field: 'mitoCn',
    format: val => val && val.toFixed(0),
    comment: 'CN = (2*mean mtDNA coverage)/(median nuclear coverage). Median for blood samples ≈ 250. CN is typically higher in other tissues. Low values may indicate mtDNA depletion.',
  },
  { title: 'Heteroplasmy Level', field: 'hl', format: val => val && val.toPrecision(2) },
  { title: 'Contamination', field: 'contamination' },
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
  ({ shouldHide, title, field, variantField, format, comment }) => {
    const value = genotype[field] || variant[variantField]
    return value && !(shouldHide && shouldHide(value, variant)) ? (
      <div key={title}>
        {`${title}:  `}
        <b>{format ? format(value, genesById) : value}</b>
        {comment && <ColoredDiv color="grey">{comment}</ColoredDiv> }
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

const getWarningsForGenotype = (genotype, variant, individual, isHemiX, isCompoundHet) => {
  const hasCnCall = isCalled(genotype.cn)
  if (!hasCnCall && !isCalled(genotype.numAlt)) {
    return <b>NO CALL</b>
  }

  const warnings = []
  if (genotype.defragged) {
    warnings.push('Defragged')
  } else if (!isHemiX && isHemiUPDVariant(genotype.numAlt, variant, individual)) {
    warnings.push('Potential UPD/ Hemizygosity')
  } else if (isCompoundHet &&
    [individual.maternalGuid, individual.paternalGuid].every(missingParentVariant(variant))) {
    warnings.push('Variant absent in parents')
  }

  if (hasCnCall) {
    const cnWarning = getGentoypeCnWarning(genotype, variant.svType, isHemiX)
    if (cnWarning) {
      warnings.push(cnWarning)
    }
  }

  if (genotype.contamination) {
    warnings.push(`Contamination (${genotype.contamination}) > 0`)
  }

  if (variant.commonLowHeteroplasmy && genotype.hl > 0) {
    warnings.push('Common low heteroplasmy')
  }
  return warnings.join(', ')
}

const PreviousCall = ({ genotype, isHemiX }) => {
  let previousCall
  if (genotype.newCall) {
    previousCall = { content: 'New Call', hover: 'No overlap in previous callset', color: 'green' }
  } else if (genotype.prevCall) {
    previousCall = { content: 'Identical Call', hover: 'Identical call in previous callset', color: 'blue' }
  } else if (genotype.prevOverlap) {
    previousCall = { content: 'Overlapping Call', hover: 'Overlapping call in previous callset', color: 'teal' }
  } else if (Number.isInteger(genotype.prevNumAlt)) {
    const hasSameHemiXGenotype = isHemiX && (genotype.numAlt === 1 || genotype.numAlt === 2) &&
      (genotype.prevNumAlt === 1 || genotype.prevNumAlt === 2)
    previousCall = {
      content: 'New Genotype',
      color: 'olive',
      hover: (
        <span>
          Previous callset:
          <AlleleContainer>{svNumAltGenotype(genotype.prevNumAlt, isHemiX)}</AlleleContainer>
          {/* eslint-disable-next-line react/jsx-one-expression-per-line */}
          {hasSameHemiXGenotype && <i>Hemi alt allele change: {genotype.prevNumAlt} to {genotype.numAlt}</i>}
        </span>
      ),
    }
  }

  return (
    <div>
      {previousCall && (
      <Popup
        content={previousCall.hover}
        position="bottom"
        trigger={<Label horizontal size="mini" content={previousCall.content} color={previousCall.color} />}
      />
      )}
    </div>
  )
}

PreviousCall.propTypes = {
  genotype: PropTypes.object,
  isHemiX: PropTypes.bool,
}

const GenotypeQuality = ({ genotype, variant }) => {
  const showSecondaryQuality = !variant.svType && genotype.numAlt >= 0
  const secondaryQuality = genotype.ab || genotype.hl
  const quality = Number.isInteger(genotype.gq) ? genotype.gq : genotype.qs
  const filters = genotype.filters?.join(', ') || variant.genotypeFilters

  return (
    <div>
      {genotype.sampleType && `${genotype.sampleType}: `}
      {Number.isInteger(quality) ? quality : '-'}
      {showSecondaryQuality && `, ${secondaryQuality ? secondaryQuality.toPrecision(2) : '-'}`}
      {filters && (
        <small>
          <br />
          {filters}
        </small>
      )}
    </div>
  )
}

GenotypeQuality.propTypes = {
  genotype: PropTypes.object,
  variant: PropTypes.object,
}

const LegacyAdditionalSampleTypePopup = ({ genotype, variant, isHemiX, genesById }) => {
  const hasConflictingNumAlt = genotype.otherSample && genotype.otherSample.numAlt !== genotype.numAlt

  return (
    <div>
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
    </div>
  )
}

LegacyAdditionalSampleTypePopup.propTypes = {
  genotype: PropTypes.object,
  variant: PropTypes.object,
  isHemiX: PropTypes.bool,
  genesById: PropTypes.object,
}

export const MultiSampleTypeAlleles = React.memo(({ genotypes, variant, individual, isHemiX, isCompoundHet }) => {
  const warnings = genotypes.reduce((acc, genotype) => {
    const warning = getWarningsForGenotype(genotype, variant, individual, isHemiX, isCompoundHet)
    if (warning) {
      acc[genotype.sampleType] = warning
    }
    return acc
  }, {})

  const hasDifferentNumAlt = genotypes.some(genotype => genotype.numAlt !== genotypes[0].numAlt)

  return (
    <Alleles
      genotype={genotypes[0]}
      variant={variant}
      isHemiX={isHemiX}
      warning={(Object.keys(warnings).length > 0 || hasDifferentNumAlt) && (
        <div>
          {Object.entries(warnings).map(([sampleType, warning]) => (
            <div key={sampleType}>
              <b>
                {sampleType}
                Warning:
              </b>
              {warning}
            </div>
          ))}
          {hasDifferentNumAlt && (
            <span>
              <b>Warning: </b>
              Genotypes differ across sample types
              {genotypes.map(genotype => (
                <div key={genotype.sampleType}>
                  {genotype.sampleType}
                  :
                  <AlleleContainer>
                    <AllelesHeader genotype={genotype} variant={variant} isHemiX={isHemiX} />
                  </AlleleContainer>
                </div>
              ))}
            </span>
          )}
        </div>
      )}
    />
  )
})

MultiSampleTypeAlleles.propTypes = {
  genotypes: PropTypes.arrayOf(PropTypes.object),
  variant: PropTypes.object,
  individual: PropTypes.object,
  isHemiX: PropTypes.bool,
  isCompoundHet: PropTypes.bool,
}

const Genotype = React.memo(({ variant, individual, isCompoundHet, genesById }) => {
  const individualGenotypes = variant.genotypes[individual.individualGuid]
  if (!individualGenotypes) {
    return null
  }
  const genotypes = (Array.isArray(individualGenotypes) ? individualGenotypes : [individualGenotypes]).sort(
    (a, b) => SAMPLE_TYPE_DISPLAY_ORDER.indexOf(a.sampleType) - SAMPLE_TYPE_DISPLAY_ORDER.indexOf(b.sampleType),
  )

  const isHemiX = isHemiXVariant(variant, individual)

  const allDetails = genotypes.map(genotype => genotypeDetails(genotype, variant, genesById)).reduce(
    (acc, genotypeDetail, index) => {
      if (index > 0) {
        acc.push(<Divider />)
      }
      return acc.concat(genotypeDetail)
    }, [],
  )

  const content = (
    <span>
      {genotypes.length === 1 ? (
        <span>
          <LegacyAdditionalSampleTypePopup
            genotype={genotypes[0]}
            variant={variant}
            isHemiX={isHemiX}
            genesById={genesById}
          />
          <Alleles
            genotype={genotypes[0]}
            variant={variant}
            isHemiX={isHemiX}
            warning={
              <div>
                <b>Warning: </b>
                {getWarningsForGenotype(genotypes[0], variant, individual, isHemiX, isCompoundHet)}
              </div>
            }
          />
        </span>
      ) : (
        <MultiSampleTypeAlleles
          genotypes={genotypes}
          variant={variant}
          individual={individual}
          isHemiX={isHemiX}
          isCompoundHet={isCompoundHet}
        />
      )}
      {genotypes.map(genotype => (
        <div key={genotype.sampleType || genotype.sampleId}>
          <PreviousCall genotype={genotype} isHemiX={isHemiX} />
          <GenotypeQuality variant={variant} genotype={genotype} />
        </div>
      ))}
    </span>
  )

  return allDetails.length ? <Popup position="top center" trigger={content} content={allDetails} /> : content
})

Genotype.propTypes = {
  variant: PropTypes.object,
  individual: PropTypes.object,
  isCompoundHet: PropTypes.bool,
  genesById: PropTypes.object,
}

const INDIVIDUAL_DETAIL_FIELDS = [INDIVIDUAL_FIELD_FEATURES]
const VARIANT_INDIVIDUAL_DETAIL_FIELDS = [
  INDIVIDUAL_FIELD_FILTER_FLAGS, INDIVIDUAL_FIELD_POP_FILTERS, ...INDIVIDUAL_DETAIL_FIELDS,
]
const SV_INDIVIDUAL_DETAIL_FIELDS = [INDIVIDUAL_FIELD_SV_FLAGS, ...INDIVIDUAL_DETAIL_FIELDS]

const IndividualDetailField = ({ field, individual }) => {
  const { individualFields, ...fieldProps } = INDIVIDUAL_FIELD_LOOKUP[field]
  const individualProps = individualFields ? individualFields(individual) : {}
  return (
    <BaseFieldView
      field={field}
      initialValues={individual}
      {...individualProps}
      {...fieldProps}
      compact
      blockDisplay
    />
  )
}

IndividualDetailField.propTypes = {
  individual: PropTypes.object,
  field: PropTypes.string,
}

const BaseVariantIndividuals = React.memo(({ variant, individuals, isCompoundHet, genesById }) => (
  <IndividualsContainer>
    {(individuals || []).map(individual => (
      <IndividualCell key={individual.individualGuid} numIndividuals={individuals.length}>
        <PedigreeIcon
          sex={individual.sex}
          affected={individual.affected}
          label={(
            <small>
              {individual.displayName}
              {variant.svType && individual[INDIVIDUAL_FIELD_SV_FLAGS] && <WarningIcon />}
            </small>
          )}
          popupHeader={individual.displayName}
          popupContent={(variant.svType ? SV_INDIVIDUAL_DETAIL_FIELDS : VARIANT_INDIVIDUAL_DETAIL_FIELDS).map(field => (
            <IndividualDetailField key={field} field={field} individual={individual} />
          ))}
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

export const FamilyVariantIndividuals = connect(mapStateToProps)(BaseVariantIndividuals)

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

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Popup, Label, Icon } from 'semantic-ui-react'

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

const isHemiUPDVariant = (numAlt, variant, individual) =>
  numAlt === 2 && [individual.maternalGuid, individual.paternalGuid].some((parentGuid) => {
    const parentGenotype = variant.genotypes[parentGuid] || {}
    return parentGenotype.numAlt === 0 && parentGenotype.affected !== 'A'
  })

const Allele = ({ isAlt, variant }) => {
  const allele = isAlt ? variant.alt : variant.ref
  let alleleText = allele.substring(0, 3)
  if (allele.length > 3) {
    alleleText += '...'
  }

  return isAlt ? <b><i>{alleleText}</i></b> : alleleText
}

Allele.propTypes = {
  isAlt: PropTypes.bool,
  variant: PropTypes.object,
}

export const Alleles = ({ numAlt, variant, isHemiUPD, isHemiX }) =>
  <AlleleContainer>
    {isHemiUPD &&
      <Popup
        flowing
        trigger={<Icon name="warning sign" color="yellow" />}
        content={<div><b>Warning:</b> Potential UPD/ Hemizygosity</div>}
      />
    }
    <Allele isAlt={numAlt > (isHemiX ? 0 : 1)} variant={variant} />/{isHemiX ? '-' : <Allele isAlt={numAlt > 0} variant={variant} />}
  </AlleleContainer>

Alleles.propTypes = {
  numAlt: PropTypes.number,
  variant: PropTypes.object,
  isHemiUPD: PropTypes.bool,
  isHemiX: PropTypes.bool,
}


const Genotype = ({ variant, individual }) => {
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
      value: variant.originalAltAlleles.join(', '),
      shouldHide: variant.originalAltAlleles.length < 1 ||
      (variant.originalAltAlleles.length === 1 && variant.originalAltAlleles[0] === variant.alt),
    },
    { title: 'Allelic Depth', value: genotype.ad },
    { title: 'Read Depth', value: genotype.dp },
    { title: 'Genotype Quality', value: genotype.gq },
    { title: 'Allelic Balance', value: genotype.ab && genotype.ab.toPrecision(2) },
    { title: 'Filter', value: variant.genotypeFilters },
    { title: 'Phred Likelihoods', value: genotype.pl },
  ]
  const isHemiX = isHemiXVariant(variant, individual)
  const isHemiUPD = !isHemiX && isHemiUPDVariant(genotype.numAlt, variant, individual)
  return [
    genotype.numAlt >= 0 ?
      <Popup
        key="alleles"
        position="top center"
        flowing
        trigger={
          <span>
            <Alleles numAlt={genotype.numAlt} variant={variant} isHemiX={isHemiX} isHemiUPD={isHemiUPD} />
            <VerticalSpacer width={5} />
            {genotype.gq || '-'}, {genotype.ab ? genotype.ab.toPrecision(2) : '-'}
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
      : <b key="no-call">NO CALL</b>,
    // TODO currently not returned from ES
    (genotype.cnvs && genotype.cnvs.cn !== null) ?
      <Popup
        key="cnvs"
        position="top center"
        content={
          <span>
            Copy Number: {genotype.cnvs.cn}<br />
            LRR median:{genotype.cnvs.LRR_median}<br />
            LRR stdev: {genotype.cnvs.LRR_sd}<br />
            SNPs supporting call: {genotype.cnvs.snps}<br />
            Size: {genotype.cnvs.size}<br />
            Found in: {parseInt(genotype.cnvs.freq, 10) - 1} other samples<br />
            Type: {genotype.cnvs.type}<br />
            Array: {genotype.cnvs.array.replace(/_/g, ' ')}<br />
            Caller: {genotype.cnvs.caller}<br />
          </span>
        }
        trigger={
          <span>
            <HorizontalSpacer width={5} />
            <Label color="red" size="small" horizontal>
              CNV: {genotype.cnvs.cn > 2 ? 'Duplication' : 'Deletion'}
            </Label>
          </span>
        }
      /> : null,
  ]
}


const VariantIndividuals = ({ variant, individuals, familyGuid }) => (
  <IndividualsContainer>
    {(individuals || []).map(individual =>
      <IndividualCell key={individual.individualGuid}>
        <PedigreeIcon
          sex={individual.sex}
          affected={individual.affected}
          label={<small>{individual.displayName}</small>}
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
        <Genotype variant={variant} individual={individual} />
      </IndividualCell>,
    )}
    <ShowReadsButton familyGuid={familyGuid} igvId={variant.variantId} />
  </IndividualsContainer>
)

VariantIndividuals.propTypes = {
  familyGuid: PropTypes.string,
  variant: PropTypes.object,
  individuals: PropTypes.array,
}

const mapStateToProps = (state, ownProps) => ({
  individuals: getSortedIndividualsByFamily(state)[ownProps.familyGuid],
})

export default connect(mapStateToProps)(VariantIndividuals)

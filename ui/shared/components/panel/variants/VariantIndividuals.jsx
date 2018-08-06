import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Popup, Label, Icon } from 'semantic-ui-react'

import { getIndividualsByGuid } from 'redux/selectors'
import ShowReadsButton from '../../buttons/ShowReadsButton'
import PedigreeIcon from '../../icons/PedigreeIcon'
import { HorizontalSpacer, VerticalSpacer } from '../../Spacers'
import PhenotipsDataPanel, { hasPhenotipsDetails } from '../view-phenotips-info/PhenotipsDataPanel'


const IndividualCell = styled.div`
  display: inline-block;
  vertical-align: top;
  text-align: center;
  padding-right: 20px;
  
  .ui.header {
    padding-top: 3px;
  }
`

const Allele = styled.span`
  color: black;
  font-size: 1.2em;
  font-weight: ${(props) => { return props.isRef ? 'inherit' : 'bolder' }};
  font-style: ${(props) => { return props.isRef ? 'inherit' : 'italic' }};
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

const isHemiVariant = (variant, individual) =>
  individual.sex === 'M' && (variant.chrom === 'X' || variant.chrom === 'Y') &&
  PAR_REGIONS[variant.genomeVersion][variant.chrom].every(region => !(region[0] < variant.pos < region[1]))

const Alleles = ({ alleles, variant, individual }) => {
  alleles = alleles.map((allele) => {
    let alleleText = allele.substring(0, 3)
    if (allele.length > 3) {
      alleleText += '..'
    }
    return { text: alleleText, isRef: allele === variant.ref }
  })

  let hemiError = null
  if (isHemiVariant(variant, individual)) {
    if (alleles[0].text !== alleles[1].text) {
      hemiError = <Popup content="WARNING: Heterozygous Male" trigger={<Icon name="warning sign" color="red" />} />
    } else {
      alleles[1] = { text: '-' }
    }
  }
  return (
    <span>
      {hemiError}
      <Allele isRef={alleles[0].isRef}>{alleles[0].text}</Allele>/<Allele isRef={alleles[1].isRef}>{alleles[1].text}</Allele>
    </span>
  )
}

Alleles.propTypes = {
  alleles: PropTypes.array,
  variant: PropTypes.object,
  individual: PropTypes.object,
}


const Genotype = ({ variant, individual }) => {
  const genotype = variant.genotypes && variant.genotypes[individual.individualId]
  if (!genotype) {
    return null
  }

  const qualityDetails = [
    {
      title: 'Raw Alt. Alleles',
      value: variant.origAltAlleles.join(', '),
      shouldHide: variant.origAltAlleles.length < 1 ||
      (variant.origAltAlleles.length === 1 && variant.origAltAlleles[0] === variant.alt),
    },
    { title: 'Allelic Depth', value: genotype.ad },
    { title: 'Read Depth', value: genotype.dp },
    { title: 'Genotype Quality', value: genotype.gq },
    { title: 'Allelic Balance', value: genotype.ab && genotype.ab.toPrecision(2) },
    { title: 'Filter', value: genotype.filter, shouldHide: genotype.filter === 'pass' },
    { title: 'Phred Likelihoods', value: genotype.pl },
  ]
  return [
    genotype.alleles.length > 0 && genotype.numAlt !== -1 ?
      <Popup
        key="alleles"
        position="top center"
        flowing
        trigger={
          <span>
            <Alleles alleles={genotype.alleles} variant={variant} individual={individual} />
            <VerticalSpacer width={5} />
            {genotype.gq || '-'}, {genotype.ab ? genotype.ab.toPrecision(2) : '-'}
            {genotype.filter && genotype.filter !== 'pass' && <small><br />{genotype.filter}</small>}
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
    genotype.cnvs.cn !== null ?
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


const VariantIndividuals = ({ variant, individualsByGuid }) => {
  const individuals = Object.values(individualsByGuid).filter(individual => individual.familyGuid === variant.familyGuid)
  individuals.sort((a, b) => a.affected.localeCompare(b.affected))
  return (
    <div>
      {individuals.map(individual =>
        <IndividualCell key={individual.individualGuid}>
          <PedigreeIcon
            sex={individual.sex}
            affected={individual.affected}
            label={<small>{individual.displayName || individual.individualId}</small>}
            popupContent={
              hasPhenotipsDetails(individual.phenotipsData) ?
                <PhenotipsDataPanel
                  individual={individual}
                  showDetails showEditPhenotipsLink={false}
                  showViewPhenotipsLink={false}
                /> : null
            }
          />
          <br />
          <Genotype variant={variant} individual={individual} />
        </IndividualCell>,
      )}
      <ShowReadsButton familyGuid={variant.familyGuid} variant={variant} />
    </div>
  )
}

VariantIndividuals.propTypes = {
  variant: PropTypes.object,
  individualsByGuid: PropTypes.object,
}

const mapStateToProps = state => ({
  individualsByGuid: getIndividualsByGuid(state),
})

export default connect(mapStateToProps)(VariantIndividuals)

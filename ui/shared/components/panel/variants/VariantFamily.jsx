import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import { Popup, Label, Header } from 'semantic-ui-react'

import { getFamiliesByGuid, getIndividualsByGuid } from 'redux/selectors'
import { getProject } from 'pages/Project/selectors'
import {
  FAMILY_FIELD_DESCRIPTION,
  FAMILY_FIELD_ANALYSIS_NOTES,
  FAMILY_FIELD_ANALYSIS_SUMMARY,
  FAMILY_FIELD_INTERNAL_NOTES,
  FAMILY_FIELD_INTERNAL_SUMMARY,
} from 'shared/utils/constants'
import PedigreeIcon from '../../icons/PedigreeIcon'
import { HorizontalSpacer } from '../../Spacers'
import Family from '../family'
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

const FAMILY_FIELDS = [
  { id: FAMILY_FIELD_DESCRIPTION },
  { id: FAMILY_FIELD_ANALYSIS_NOTES },
  { id: FAMILY_FIELD_ANALYSIS_SUMMARY },
  { id: FAMILY_FIELD_INTERNAL_NOTES },
  { id: FAMILY_FIELD_INTERNAL_SUMMARY },
]

const Alleles = ({ alleles, variant, individual }) => {
  alleles = alleles.map((allele) => {
    let alleleText = allele.substring(0, 3)
    if (allele.length > 3) {
      alleleText += '..'
    }
    return { text: alleleText, isRef: allele === variant.ref }
  })
  if (variant.chrom === 'X' && individual.sex === 'M') {
    if (alleles[0].text !== alleles[1].text) {
      console.log(`Invalid genotype for male ${individual.individualId}: multiple alleles found on the X chromosome`)
      alleles = [{ text: '?' }, { text: '?' }]
    } else {
      alleles[1] = { text: '-' }
    }
  }
  return (
    <span>
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
            <HorizontalSpacer width={5} />
            ({genotype.gq || '?'}, {genotype.ab ? genotype.ab.toPrecision(2) : '?'})
            {genotype.filter && genotype.filter !== 'pass' && <span><br />{genotype.filter}</span>}
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


const VariantFamily = ({ variant, project, family, individualsByGuid }) => {
  if (!family) {
    return null
  }
  const individuals = family.individualGuids.map(individualGuid => individualsByGuid[individualGuid])
  individuals.sort((a, b) => a.affected.localeCompare(b.affected))
  return (
    <div>
      <IndividualCell>
        <Header size="small">
          Family<HorizontalSpacer width={5} />
          <Popup
            hoverable
            wide="very"
            position="top left"
            trigger={
              <Link to={`/project/${project.projectGuid}/saved_variants/family/${family.familyGuid}`}>
                {family.displayName}
              </Link>
            }
            content={<Family family={family} fields={FAMILY_FIELDS} useFullWidth disablePedigreeZoom />}
          />
        </Header>
      </IndividualCell>
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
    </div>
  )
}

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

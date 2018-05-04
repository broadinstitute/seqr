import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import { Popup, Label, Header } from 'semantic-ui-react'

import { getFamiliesByGuid, getIndividualsByGuid } from 'redux/rootReducer'
import { getProject } from 'pages/Project/reducers'
import PedigreeIcon from '../../icons/PedigreeIcon'
import { HorizontalSpacer } from '../../Spacers'
import Family from '../family'


const IndividualCell = styled.div`
  display: inline-block;
  vertical-align: top;
  text-align: center;
  padding: 0 10px;
  
  .alleles {
    color: black;
    font-size: 1.2em;
    
    .alt {
      font-weight: bolder;
      font-style: italic;
    }
  }
`

const Alleles = ({ alleles, variant }) => {
  alleles = alleles.map((allele) => {
    let alleleText = allele.substring(0, 3)
    if (allele.length > 3) {
      alleleText += '..'
    }
    return { text: alleleText, class: allele === variant.ref ? 'ref' : 'alt' }
  })
  return (
    <span className="alleles">
      <span className={alleles[0].class}>{alleles[0].text}</span>/<span className={alleles[1].class}>{alleles[1].text}</span>
    </span>
  )
}

Alleles.propTypes = {
  alleles: PropTypes.array,
  variant: PropTypes.object,
}


const VariantFamily = ({ variant, project, family, individualsByGuid }) => {
  const individuals = family.individualGuids.map(individualGuid => individualsByGuid[individualGuid])
  individuals.sort((a, b) => a.affected.localeCompare(b.affected))
  return (
    <div>
      <IndividualCell>
        <Header size="small" >
          Family<HorizontalSpacer width={5} />
          <Popup
            flowing
            hoverable
            position="top center"
            trigger={
              <Link to={`/project/${project.projectGuid}/saved_variants/family/${family.familyGuid}`}>
                {family.displayName}
              </Link>
            }
            content={<Family family={family} showInternalFields showDetails useFullWidth canEdit={false} />}
          />
        </Header>
      </IndividualCell>
      {individuals.map((individual) => {
        const genotype = variant.genotypes && variant.genotypes[individual.individualId]

        const qualityDetails = genotype ? [
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
        ] : []

        const variantIndividual =
          <IndividualCell key={individual.individualGuid}>
            <PedigreeIcon sex={individual.sex} affected={individual.affected} />
            <small>{individual.displayName || individual.individualId}</small>
            <br />
            {genotype && genotype.alleles.length === 2 && genotype.numAlt !== -1 ?
              <span>
                <Alleles alleles={genotype.alleles} variant={variant} />
                <HorizontalSpacer width={5} />
                ({genotype.gq || '?'}, {genotype.ab ? genotype.ab.toPrecision(2) : '?'})
                {genotype.filter && genotype.filter !== 'pass' && <span><br />Filter: {genotype.filter}</span>}
              </span>
              : <b>NO CALL</b>
            }
            {genotype && genotype.cnvs.cn !== null &&
            <Popup
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
            />
            }
          </IndividualCell>

        return genotype && genotype.alleles.length > 0 ?
          <Popup
            key={individual.individualGuid}
            position="top center"
            flowing
            trigger={variantIndividual}
            content={
              qualityDetails.map(({ shouldHide, title, value }) => {
                return value && !shouldHide ?
                  <div key={title}>{title}:<HorizontalSpacer width={10} /><b>{value}</b></div> : null
              })
            }
          />
          : variantIndividual
      })}
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

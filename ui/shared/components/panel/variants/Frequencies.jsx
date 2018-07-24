import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Popup } from 'semantic-ui-react'

import { HorizontalSpacer } from '../../Spacers'

const FreqValue = styled.span`
  font-weight: bolder;
  color: ${props => (props.hasLink ? 'inherit' : 'grey')};
`

const FreqLink = ({ url, value, variant, genomeVersion }) => {
  let { chrom, pos } = variant
  if (variant.liftedOverGenomeVersion === genomeVersion) {
    chrom = variant.liftedOverChrom
    pos = variant.liftedOverPos
  }

  const isRegion = parseInt(value, 10) <= 0
  let coords
  if (isRegion) {
    coords = `${chrom}-${parseInt(pos, 10) - 100}-${parseInt(pos, 10) + 100}`
  } else {
    coords = `${chrom}-${pos}-${variant.ref}-${variant.alt}`
  }

  return (
    <a href={`http://${url}/${isRegion ? 'region' : 'variant'}/${coords}`} target="_blank" rel="noopener noreferrer">
      <FreqValue hasLink>{value}</FreqValue>
    </a>
  )
}

FreqLink.propTypes = {
  url: PropTypes.string.isRequired,
  value: PropTypes.string,
  variant: PropTypes.object.isRequired,
  genomeVersion: PropTypes.string.isRequired,
}

const FreqSummary = ({ field, fieldTitle, variant, url, hasLink, showAC, genomeVersion = '37', precision = 2 }) => {
  const { freqs, popCounts } = variant.annotation
  if (freqs[field] === null) {
    return null
  }
  const value = freqs[field] > 0 ? freqs[field].toPrecision(precision) : '0.0'
  return (
    <div>
      {fieldTitle || field.replace('_', ' ').toUpperCase()}<HorizontalSpacer width={5} />
      {hasLink ?
        <FreqLink
          url={url || `${field.split('_')[0]}.broadinstitute.org`}
          value={value}
          variant={variant}
          genomeVersion={genomeVersion}
        /> :
        <FreqValue>{value}</FreqValue>
      }
      {popCounts[`${field}_hom`] !== null && popCounts[`${field}_hom`] !== undefined &&
        <span><HorizontalSpacer width={5} />Hom={popCounts[`${field}_hom`]}</span>
      }
      {popCounts[`${field}_hemi`] !== null && popCounts[`${field}_hemi`] !== undefined &&
        variant.chrom.endsWith('X') &&
        <span><HorizontalSpacer width={5} />Hemi={popCounts[`${field}_hemi`]}</span>
      }
      {showAC && popCounts.AC !== null && <span><HorizontalSpacer width={5} />AC={popCounts.AC} out of {popCounts.AN}</span>}
    </div>
  )
}

FreqSummary.propTypes = {
  field: PropTypes.string.isRequired,
  variant: PropTypes.object.isRequired,
  precision: PropTypes.number,
  fieldTitle: PropTypes.string,
  url: PropTypes.string,
  hasLink: PropTypes.bool,
  showAC: PropTypes.bool,
  genomeVersion: PropTypes.string,
}

const Frequencies = ({ variant }) => {
  if (!variant.annotation.freqs) {
    return null
  }
  const { popCounts } = variant.annotation

  const freqContent = (
    <div>
      <FreqSummary field="AF" fieldTitle="THIS CALLSET" variant={variant} showAC />
      <FreqSummary field="g1k" fieldTitle="1KG WGS" variant={variant} />
      <FreqSummary field="exac" variant={variant} hasLink />
      <FreqSummary field="gnomad_exomes" variant={variant} hasLink />
      <FreqSummary field="gnomad_genomes" variant={variant} precision={3} hasLink />
      <FreqSummary
        field="topmedAF"
        fieldTitle="TOPMED"
        variant={variant}
        genomeVersion="38"
        precision={3}
        url="bravo.sph.umich.edu/freeze5/hg38"
        hasLink
      />
    </div>
  )

  return (
    popCounts.AC || popCounts.gnomadExomesAC || popCounts.gnomadGenomesAC || popCounts.topmedAC ?
      <Popup
        position="top center"
        flowing
        trigger={freqContent}
        header="Allele Counts"
        content={
          <div>
            <div>This callset:<HorizontalSpacer width={10} /><b>{popCounts.AC}</b></div>
            <div>Gnomad exomes:<HorizontalSpacer width={10} /><b>{popCounts.gnomadExomesAC}</b></div>
            <div>Gnomad genomes:<HorizontalSpacer width={10} /><b>{popCounts.gnomadGenomesAC}</b></div>
            <div>Topmed:<HorizontalSpacer width={10} /><b>{popCounts.topmedAC}</b></div>
          </div>
        }
      />
      : freqContent
  )
}

Frequencies.propTypes = {
  variant: PropTypes.object,
}

export default Frequencies

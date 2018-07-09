import React from 'react'
import PropTypes from 'prop-types'
import { Popup } from 'semantic-ui-react'

import { HorizontalSpacer } from '../../Spacers'

const FreqLink = ({ url, value, variant, genomeVersion, precision }) => {
  let { chrom, pos } = variant
  if (variant.liftedOverGenomeVersion === genomeVersion) {
    chrom = variant.liftedOverChrom
    pos = variant.liftedOverPos
  }

  let coords
  if (value <= 0) {
    coords = `${chrom}-${parseInt(pos, 10) - 100}-${parseInt(pos, 10) + 100}`
  } else {
    coords = `${chrom}-${pos}-${variant.ref}-${variant.alt}`
  }

  return (
    <a target="_blank" href={`http://${url}/${value > 0 ? 'variant' : 'region'}/${coords}`}>
      {value > 0 ? value.toPrecision(precision || 2) : '0.0'}
    </a>
  )
}

FreqLink.propTypes = {
  url: PropTypes.string.isRequired,
  value: PropTypes.number,
  variant: PropTypes.object.isRequired,
  genomeVersion: PropTypes.string.isRequired,
  precision: PropTypes.number,
}

const FreqSummary = ({ field, variant, precision }) => {
  const { freqs, popCounts } = variant.annotation
  if (freqs[field] === null) {
    return null
  }
  const url = `${field.split('_')[0]}.broadinstitute.org`
  return (
    <div>
      <b>{field.replace('_', ' ').toUpperCase()}</b><HorizontalSpacer width={5} />
      <FreqLink url={url} value={freqs[field]} variant={variant} genomeVersion="37" precision={precision} />
      {popCounts[`${field}_hom`] !== null &&
        <span><HorizontalSpacer width={5} />Hom={popCounts[`${field}_hom`]}</span>
      }
      {popCounts[`${field}_hemi`] !== null && variant.chrom.endsWith('X') &&
        <span><HorizontalSpacer width={5} />Hemi={popCounts[`${field}_hemi`]}</span>
      }
    </div>
  )
}

FreqSummary.propTypes = {
  field: PropTypes.string.isRequired,
  variant: PropTypes.object.isRequired,
  precision: PropTypes.number,
}

const Frequencies = ({ variant }) => {
  if (!variant.annotation.freqs) {
    return null
  }
  const { freqs, popCounts } = variant.annotation

  const freqContent = (
    <div>
      {freqs.AF !== null &&
        <div>
          <b>THIS CALLSET</b><HorizontalSpacer width={5} />{freqs.AF.toPrecision(2)}<HorizontalSpacer width={5} />
          {popCounts.AC !== null && <span>AC={popCounts.AC} out of {popCounts.AN}</span>}
        </div>
      }
      <div>
        <b>1KG WGS</b><HorizontalSpacer width={5} />
        {freqs.g1k.toPrecision(2)}
      </div>
      <FreqSummary field="exac" variant={variant} />
      <FreqSummary field="gnomad_exomes" variant={variant} />
      <FreqSummary field="gnomad_genomes" variant={variant} precision={3} />
      {freqs.topmedAF !== null &&
        <div>
          <b>TOPMED</b><HorizontalSpacer width={5} />
          <FreqLink
            url="bravo.sph.umich.edu/freeze5/hg38"
            value={freqs.topmedAF}
            variant={variant}
            genomeVersion="38"
            precision={3}
          />
        </div>
      }
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

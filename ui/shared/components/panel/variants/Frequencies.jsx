import React from 'react'
import PropTypes from 'prop-types'
import { Grid, Popup } from 'semantic-ui-react'

import { HorizontalSpacer } from '../../Spacers'

const getFreq = (freqs, field) =>
  freqs[`${field}_popmax_AF`] || freqs[`${field}_AF`] || freqs[`${field}_popmax`] || freqs[field] || 0

const FreqLink = ({ url, value, coords, precision }) => {
  if (value <= 0) {
    const coordSplit = coords.split('-')
    const coordPos = parseInt(coordSplit[1], 10)
    coords = `${coordSplit[0]}-${coordPos - 100}-${coordPos + 100}`
  }
  return (
    <a target="_blank" href={`http://${url}/${value > 0 ? 'variant' : 'region'}/${coords}`}>
      {value > 0 ? value.toPrecision(precision || 2) : 0.0}
    </a>
  )
}

FreqLink.propTypes = {
  url: PropTypes.string.isRequired,
  value: PropTypes.number,
  coords: PropTypes.string.isRequired,
  precision: PropTypes.number,
}

const FreqSummary = ({ field, secondaryField, variant, title, precision }) => {
  const popCounts = variant.annotation.pop_counts
  const coords = variant.extras.grch37_coords || `${variant.chr}-${variant.pos}-${variant.ref}-${variant.alt}`
  let value = getFreq(variant.annotation.freqs, field)
  if (!value && secondaryField) {
    value = getFreq(variant.annotation.freqs, secondaryField)
  }
  return (
    <div>
      <b>{title || field.replace('_', ' ').toUpperCase()}</b><HorizontalSpacer width={5} />
      <FreqLink url={`${field.split('_')[0]}.broadinstitute.org`} value={value} coords={coords} precision={precision} />
      {popCounts && `${field}_Hom` in popCounts &&
        <span><HorizontalSpacer width={5} />Hom={popCounts[`${field}_Hom`]}</span>
      }
      {popCounts && `${field}_Hemi` in popCounts && variant.chrom.endsWith('X') &&
        <span><HorizontalSpacer width={5} />Hemi={popCounts[`${field}_Hemi`]}</span>
      }
    </div>
  )
}

FreqSummary.propTypes = {
  field: PropTypes.string.isRequired,
  secondaryField: PropTypes.string,
  variant: PropTypes.object.isRequired,
  title: PropTypes.string,
  precision: PropTypes.number,
}

const Frequencies = ({ variant }) => {
  if (!variant.annotation || !variant.annotation.freqs) {
    return null
  }
  const { freqs, pop_counts: popCounts } = variant.annotation

  const freqContent = (
    <div>
      {freqs.AF &&
        <div>
          <b>THIS CALLSET</b>{freqs.AF.toPrecision(2)}<HorizontalSpacer width={5} />
          {popCounts && <span>AC={popCounts.AC} out of {popCounts.AN}</span>}
        </div>
      }
      <div>
        <b>1KG WGS</b><HorizontalSpacer width={5} />
        {getFreq(freqs, '1kg_wgs') || getFreq(freqs, '1kg_wgs_phase3').toPrecision(2)}
      </div>
      <FreqSummary field="exac_v3" title="EXAC" variant={variant} />
      <FreqSummary field="gnomad_exomes" secondaryField="gnomad-exomes2" variant={variant} />
      <FreqSummary field="gnomad_genomes" secondaryField="gnomad-genomes2" variant={variant} precision={3} />
      {popCounts && 'topmed_AF' in popCounts &&
        <div>
          <b>TOPMED</b>
          <FreqLink
            url="bravo.sph.umich.edu/freeze5/hg38"
            value={popCounts.topmed_AF}
            coords={variant.extras.grch38_coords}
            precision={3}
          />
        </div>
      }
    </div>
  )

  return (
    <Grid.Column width={3}>
      {popCounts ?
        <Popup
          position="top center"
          flowing
          trigger={freqContent}
          header="Allele Counts"
          content={
            <div>
              <span>This callset:<HorizontalSpacer width={10} /><b>{popCounts.AC}</b><br /></span>
              <span>Gnomad exomes:<HorizontalSpacer width={10} /><b>{popCounts.gnomad_exomes_AC}</b><br /></span>
              <span>Gnomad genomes:<HorizontalSpacer width={10} /><b>{popCounts.gnomad_genomes_AC}</b><br /></span>
              <span>Topmed:<HorizontalSpacer width={10} /><b>{popCounts.topmed_AC}</b><br /></span>
            </div>
          }
        />
        : freqContent
      }
    </Grid.Column>
  )
}

Frequencies.propTypes = {
  variant: PropTypes.object,
}

export default Frequencies

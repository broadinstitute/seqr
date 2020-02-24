import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Popup } from 'semantic-ui-react'

import { HorizontalSpacer, VerticalSpacer } from '../../Spacers'
import { GENOME_VERSION_37, GENOME_VERSION_38 } from '../../../utils/constants'


const FreqValue = styled.span`
  color: black;
`

const FreqLink = React.memo(({ urls, value, displayValue, variant, queryParams }) => {
  let { chrom, pos, genomeVersion } = variant
  if (!urls[genomeVersion] && urls[variant.liftedOverGenomeVersion]) {
    chrom = variant.liftedOverChrom
    pos = variant.liftedOverPos
    genomeVersion = variant.liftedOverGenomeVersion
  }

  const isRegion = parseFloat(value, 10) <= 0
  let coords
  if (isRegion) {
    const posInt = parseInt(pos, 10)
    coords = `${chrom}-${posInt - 100}-${posInt + 100}`
  } else {
    coords = `${chrom}-${pos}-${variant.ref}-${variant.alt}`
  }

  const queryString = (queryParams && queryParams[genomeVersion]) ? `?${queryParams[genomeVersion]}` : ''

  return (
    <a href={`http://${urls[genomeVersion]}/${isRegion ? 'region' : 'variant'}/${coords}${queryString}`} target="_blank">
      {displayValue || value}
    </a>
  )
})

FreqLink.propTypes = {
  urls: PropTypes.object.isRequired,
  value: PropTypes.string,
  displayValue: PropTypes.string,
  variant: PropTypes.object.isRequired,
  queryParams: PropTypes.object,
}

const FreqSummary = React.memo(({ field, fieldTitle, variant, urls, queryParams, showAC, precision = 2 }) => {
  const { populations = {}, chrom } = variant
  const population = populations[field] || {}
  if (population.af === null || population.af === undefined) {
    return null
  }
  const value = population.af > 0 ? population.af.toPrecision(precision) : '0.0'
  const filterValue = population.filter_af && population.filter_af > 0 && population.filter_af.toPrecision(precision)

  const popCountDetails = [{ popField: `${field}_hom`, title: 'Hom' }]
  if (chrom.endsWith('X')) {
    popCountDetails.push({ popField: `${field}_hemi`, title: 'Hemi' })
  }
  if (showAC) {
    popCountDetails.push({ popField: 'AC', denominatorField: 'AN' })
  }

  return (
    <div>
      {fieldTitle}<HorizontalSpacer width={5} />
      <FreqValue>
        <b>
          {urls ?
            <FreqLink
              urls={urls}
              queryParams={queryParams}
              value={value}
              displayValue={filterValue}
              variant={variant}
            /> : (filterValue || value)
          }
        </b>
        {population.hom !== null && population.hom !== undefined &&
          <span><HorizontalSpacer width={5} />Hom={population.hom}</span>
        }
        {chrom.endsWith('X') && population.hemi !== null && population.hemi !== undefined &&
          <span><HorizontalSpacer width={5} />Hemi={population.hemi}</span>
        }
        {showAC && population.ac !== null && population.ac !== undefined &&
          <span><HorizontalSpacer width={5} />AC={population.ac} out of {population.an}</span>
        }
      </FreqValue>
    </div>
  )
})

FreqSummary.propTypes = {
  field: PropTypes.string.isRequired,
  variant: PropTypes.object.isRequired,
  precision: PropTypes.number,
  fieldTitle: PropTypes.string,
  urls: PropTypes.object,
  queryParams: PropTypes.object,
  showAC: PropTypes.bool,
}

const POPULATIONS = [
  { field: 'callset', fieldTitle: 'This Callset', showAC: true },
  { field: 'g1k', fieldTitle: '1kg WGS' },
  {
    field: 'exac',
    fieldTitle: 'ExAC',
    urls: { [GENOME_VERSION_37]: 'gnomad.broadinstitute.org' },
    queryParams: { [GENOME_VERSION_37]: 'dataset=exac' },
  },
  { field: 'gnomad_exomes', fieldTitle: 'gnomAD exomes', urls: { [GENOME_VERSION_37]: 'gnomad.broadinstitute.org' } },
  {
    field: 'gnomad_genomes',
    fieldTitle: 'gnomAD genomes',
    precision: 3,
    urls: { [GENOME_VERSION_37]: 'gnomad.broadinstitute.org', [GENOME_VERSION_38]: 'gnomad.broadinstitute.org' },
    queryParams: { [GENOME_VERSION_38]: 'dataset=gnomad_r3' },
  },
  {
    field: 'topmed',
    fieldTitle: 'TopMed',
    precision: 3,
    urls: {
      [GENOME_VERSION_37]: 'bravo.sph.umich.edu/freeze3a/hg19',
      [GENOME_VERSION_38]: 'bravo.sph.umich.edu/freeze5/hg38',
    },
  },
]

const Frequencies = React.memo(({ variant }) => {
  const { populations } = variant
  const freqContent = (
    <div>
      {POPULATIONS.map(pop =>
        <FreqSummary key={pop.field} variant={variant} {...pop} />,
      )}
    </div>
  )

  const hasAcPops = POPULATIONS.filter(pop => populations[pop.field].ac)
  const hasGlobalAfPops = POPULATIONS.filter(
    pop => populations[pop.field].filter_af && (populations[pop.field].filter_af !== populations[pop.field].af))

  return (
    (hasAcPops.length || hasGlobalAfPops.length) ?
      <Popup position="top center" flowing trigger={freqContent}>
        {hasGlobalAfPops.length > 0 && <Popup.Header content="Global AFs" />}
        <Popup.Content>
          {hasGlobalAfPops.map(pop =>
            <div key={pop.field}>{pop.fieldTitle}: {populations[pop.field].af.toPrecision(pop.precision || 2)}</div>,
          )}
        </Popup.Content>
        {hasGlobalAfPops.length > 0 && hasAcPops.length > 0 && <VerticalSpacer height={5} />}
        {hasAcPops.length > 0 && <Popup.Header content="Allele Counts" />}
        <Popup.Content>
          {hasAcPops.map(pop =>
            <div key={pop.field}>{pop.fieldTitle}: {populations[pop.field].ac} out of {populations[pop.field].an}</div>,
          )}
        </Popup.Content>
      </Popup>
      : freqContent
  )
})

Frequencies.propTypes = {
  variant: PropTypes.object,
}

export default Frequencies

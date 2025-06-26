import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import styled from 'styled-components'
import { Popup, Divider, Label } from 'semantic-ui-react'

import { getTotalSampleCounts } from 'redux/selectors'
import { HorizontalSpacer, VerticalSpacer } from '../../Spacers'
import {
  GNOMAD_SV_CRITERIA_MESSAGE,
  SV_CALLSET_CRITERIA_MESSAGE,
  TOPMED_FREQUENCY,
  GENOME_VERSION_37,
  GENOME_VERSION_38,
  DATASET_TYPE_SNV_INDEL_CALLS,
  DATASET_TYPE_SV_CALLS,
  DATASET_TYPE_MITO_CALLS,
  getVariantMainGeneId,
} from '../../../utils/constants'

const FreqValue = styled.span`
  color: black;
`

const FreqLink = React.memo(({ urls, value, displayValue, variant, queryParams, getPath }) => {
  let { chrom, pos, genomeVersion } = variant
  if (!urls[genomeVersion] && urls[variant.liftedOverGenomeVersion]) {
    chrom = variant.liftedOverChrom
    pos = variant.liftedOverPos
    genomeVersion = variant.liftedOverGenomeVersion
  }

  const path = getPath({ chrom, pos, genomeVersion, variant, value })

  const queryString = (queryParams && queryParams[genomeVersion]) ? `?${queryParams[genomeVersion]}` : ''

  return (
    <a href={`http://${urls[genomeVersion]}/${path}${queryString}`} target="_blank" rel="noreferrer">
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
  getPath: PropTypes.func,
}

const getFreqLinkPath = ({ chrom, pos, variant, value }) => {
  const floatValue = parseFloat(value, 10)
  const isRegion = floatValue <= 0
  let coords
  if (Number.isNaN(floatValue)) {
    coords = value
  } else if (isRegion) {
    const posInt = parseInt(pos, 10)
    const endOffset = variant.end ? variant.end - variant.pos : 0
    coords = `${chrom}-${Math.max(posInt - 100, 1)}-${posInt + endOffset + 100}`
  } else {
    coords = `${chrom}-${pos}-${variant.ref}-${variant.alt}`
  }

  return `${isRegion ? 'region' : 'variant'}/${coords}`
}

const AfDisplay = ({ population, variant, urls, queryParams, conditionalQueryParams, populations, precision = 2 }) => {
  const afValue = population.af > 0 ? population.af.toPrecision(precision) : '0.0'
  // gnomad v4 SVs use "v3" in their ID construction, but we are in fact on v4
  const value = population.id ? population.id.replace('gnomAD-SV_v3_', '') : afValue
  const displayValue = population.filter_af > 0 ? population.filter_af.toPrecision(precision) : afValue

  return urls ? (
    <FreqLink
      urls={urls}
      queryParams={conditionalQueryParams ? conditionalQueryParams(populations) : queryParams}
      value={value}
      displayValue={displayValue}
      variant={variant}
      getPath={getFreqLinkPath}
    />
  ) : displayValue
}

AfDisplay.propTypes = {
  population: PropTypes.object.isRequired,
  variant: PropTypes.object.isRequired,
  precision: PropTypes.number,
  urls: PropTypes.object,
  queryParams: PropTypes.object,
  conditionalQueryParams: PropTypes.object,
  populations: PropTypes.object,
}

const FreqSummary = React.memo((props) => {
  const { field, fieldTitle, variant, acDisplay, titleContainer, warningContainer, ...afProps } = props
  const { populations, chrom } = variant
  const population = (populations || {})[field] || {}
  const noAf = population.af === null || population.af === undefined
  if (noAf && (population.ac === null || population.ac === undefined)) {
    return null
  }

  let acDisplayValue = acDisplay && population.ac !== null && population.ac !== undefined && `${acDisplay}=${population.ac}`
  if (acDisplayValue && population.an !== null && population.an !== undefined) {
    acDisplayValue = `${acDisplayValue} out of ${population.an}`
  }
  const het = (!acDisplay &&
    (population.het === null || population.het === undefined) &&
    population.ac !== null && population.ac !== undefined &&
    population.hom !== null && population.hom !== undefined
  ) ? (population.ac - (2 * population.hom)) : population.het

  return (
    <div>
      {titleContainer ? titleContainer(props) : fieldTitle}
      <HorizontalSpacer width={5} />
      <FreqValue>
        {!noAf && (
          <b>
            <AfDisplay
              population={population}
              variant={variant}
              populations={populations}
              {...afProps}
            />
          </b>
        )}
        {population.hom !== null && population.hom !== undefined && (
          <span>
            <HorizontalSpacer width={5} />
            {`Hom=${population.hom}`}
          </span>
        )}
        {het !== null && het !== undefined && (
          <span>
            <HorizontalSpacer width={5} />
            {`Het=${het}`}
          </span>
        )}
        {chrom.endsWith('X') && population.hemi !== null && population.hemi !== undefined && (
          <span>
            <HorizontalSpacer width={5} />
            {`Hemi=${population.hemi}`}
          </span>
        )}
        {acDisplayValue && (
          <span>
            <HorizontalSpacer width={5} />
            {acDisplayValue}
          </span>
        )}
      </FreqValue>
      &nbsp;
      {warningContainer && warningContainer(population, props)}
    </div>
  )
})

FreqSummary.propTypes = {
  field: PropTypes.string.isRequired,
  variant: PropTypes.object.isRequired,
  precision: PropTypes.number,
  fieldTitle: PropTypes.string,
  titleContainer: PropTypes.func,
  warningContainer: PropTypes.func,
  urls: PropTypes.object,
  queryParams: PropTypes.object,
  conditionalQueryParams: PropTypes.object,
  acDisplay: PropTypes.string,
}

const getGenePath = ({ variant }) => `gene/${getVariantMainGeneId(variant)}`

const gnomadLink = ({ fieldTitle, esVersion, variant, ...props }) => {
  const isEs = !(variant || {}).populations?.seqr
  const [prefix, detail] = fieldTitle.split(' ')
  return (
    <span>
      <FreqLink {...props} variant={variant} displayValue={`${prefix} ${isEs ? esVersion : 'v4'}`} getPath={getGenePath} />
      &nbsp;
      {detail}
    </span>
  )
}

gnomadLink.propTypes = {
  fieldTitle: PropTypes.string,
}

const gnomadAnWarning = ({ ac, an }, { fieldTitle, maxAN, variant }) => {
  const isEs = !(variant || {}).populations?.seqr
  return (!isEs && ac && an < (maxAN / 2)) ? (
    <Popup
      trigger={<Label color="orange" content="low cov." size="mini" horizontal />}
      content={`This variant is covered in fewer than 50% of individuals in ${fieldTitle}. This may indicate a low-quality site.`}
    />
  ) : null
}

const GNOMAD_URL_INFO = {
  urls: { [GENOME_VERSION_37]: 'gnomad.broadinstitute.org', [GENOME_VERSION_38]: 'gnomad.broadinstitute.org' },
  queryParams: { [GENOME_VERSION_38]: 'dataset=gnomad_r4', [GENOME_VERSION_37]: 'dataset=gnomad_r2_1' },
}

const sectionTitle = ({ fieldTitle, section }) => (
  <span>
    {fieldTitle}
    &nbsp;
    {section.toLowerCase()}
  </span>
)

const BaseGlobalAcPopup = ({ totalSampleCounts, datasetType }) => (
  Object.keys(totalSampleCounts).length > 0 && (
    <Popup.Content>
      <i>
        The seqr allele count (AC) and homozygote count (Hom) reflect all observed occurrences of a variant in seqr.
        While not all sites may be captured in the loaded callsets, an upper bound for the total allele number (AN)
        can be estimated based on the total number of samples loaded in seqr:
      </i>
      {Object.entries(totalSampleCounts[datasetType]).map(([sampleType, count]) => (
        <div key={sampleType}>{`${sampleType}: ${count}`}</div>
      ))}
    </Popup.Content>
  )
)

BaseGlobalAcPopup.propTypes = {
  totalSampleCounts: PropTypes.object,
  datasetType: PropTypes.string,
}

const mapStateToProps = state => ({
  totalSampleCounts: getTotalSampleCounts(state),
})

const GlobalAcPopup = connect(mapStateToProps)(BaseGlobalAcPopup)

const HOM_SECTION = 'Homoplasmy'
const HET_SECTION = 'Heteroplasmy'

const SV_CALLSET_POP = { field: 'sv_callset', fieldTitle: 'This Callset', acDisplay: 'AC', helpMessage: SV_CALLSET_CRITERIA_MESSAGE }
const CALLSET_POP = { field: 'callset', fieldTitle: 'This Callset', acDisplay: 'AC' }
const SEQR_POP = { ...CALLSET_POP, field: 'seqr', fieldTitle: 'seqr' }

const POPULATIONS = [
  SV_CALLSET_POP,
  { ...SV_CALLSET_POP, field: 'sv_seqr', fieldTitle: 'seqr' },
  CALLSET_POP,
  SEQR_POP,
  {
    field: 'exac',
    fieldTitle: 'ExAC',
    urls: { [GENOME_VERSION_37]: 'gnomad.broadinstitute.org' },
    queryParams: { [GENOME_VERSION_37]: 'dataset=exac' },
  },
  {
    field: 'gnomad_exomes',
    fieldTitle: 'gnomAD exomes',
    titleContainer: gnomadLink,
    warningContainer: gnomadAnWarning,
    maxAN: 730947 * 2, // From https://gnomad.broadinstitute.org/stats
    esVersion: 'v2',
    conditionalQueryParams: populations => (populations.seqr ? GNOMAD_URL_INFO.queryParams : { [GENOME_VERSION_37]: 'dataset=gnomad_r2_1' }),
    ...GNOMAD_URL_INFO,
  },
  {
    field: 'gnomad_genomes',
    fieldTitle: 'gnomAD genomes',
    titleContainer: gnomadLink,
    warningContainer: gnomadAnWarning,
    maxAN: 76215 * 2, // From https://gnomad.broadinstitute.org/stats
    esVersion: 'v3',
    conditionalQueryParams: populations => (populations.seqr ? GNOMAD_URL_INFO.queryParams : { [GENOME_VERSION_38]: 'dataset=gnomad_r3' }),
    precision: 3,
    ...GNOMAD_URL_INFO,
  },
  {
    field: TOPMED_FREQUENCY,
    fieldTitle: 'TopMed',
    precision: 3,
    urls: {
      [GENOME_VERSION_37]: 'bravo.sph.umich.edu/freeze3a/hg19',
      [GENOME_VERSION_38]: 'bravo.sph.umich.edu/freeze5/hg38',
    },
  },
  {
    field: 'gnomad_svs',
    fieldTitle: 'gnomAD SVs',
    precision: 3,
    urls: { [GENOME_VERSION_38]: 'gnomad.broadinstitute.org' },
    queryParams: { [GENOME_VERSION_38]: 'dataset=gnomad_sv_r4' },
    helpMessage: GNOMAD_SV_CRITERIA_MESSAGE,
  },
]

const CALLSET_HET_POP = {
  field: 'callset_heteroplasmy',
  fieldTitle: 'This Callset',
  acDisplay: 'AC',
  titleContainer: sectionTitle,
  section: HET_SECTION,
}

const MITO_POPULATIONS = [
  {
    ...CALLSET_POP,
    titleContainer: sectionTitle,
    section: HOM_SECTION,
  },
  {
    ...SEQR_POP,
    titleContainer: sectionTitle,
    section: HOM_SECTION,
  },
  CALLSET_HET_POP,
  { ...CALLSET_HET_POP, field: 'seqr_heteroplasmy', fieldTitle: 'seqr' },
  {
    field: 'gnomad_mito',
    fieldTitle: 'gnomAD mito',
    titleContainer: sectionTitle,
    section: HOM_SECTION,
    precision: 3,
    ...GNOMAD_URL_INFO,
  },
  {
    field: 'gnomad_mito_heteroplasmy',
    fieldTitle: 'gnomAD mito',
    titleContainer: sectionTitle,
    section: HET_SECTION,
    precision: 3,
    ...GNOMAD_URL_INFO,
  },
  {
    field: 'helix',
    fieldTitle: 'Helix mito',
    titleContainer: sectionTitle,
    section: HOM_SECTION,
    precision: 3,
  },
  {
    field: 'helix_heteroplasmy',
    fieldTitle: 'Helix mito',
    titleContainer: sectionTitle,
    section: HET_SECTION,
    precision: 3,
  },
]

const DETAIL_SECTIONS = [
  {
    name: 'Global AFs',
    hasDetail: pop => pop && pop.filter_af && (pop.filter_af !== pop.af),
    display: () => [{ valueField: 'af' }],
  },
  {
    name: 'Allele Counts',
    hasDetail: pop => pop && pop.ac && pop.an,
    display: () => [{ valueField: 'ac' }],
  },
]

const MITO_DETAIL_SECTIONS = [
  {
    name: HOM_SECTION,
    hasDetail: pop => pop && pop.ac,
    display: () => [{ valueField: 'ac' }],
  },
  {
    name: HET_SECTION,
    hasDetail: pop => pop && (pop.ac || pop.max_hl),
    display: pop => ([
      pop.ac && { valueField: 'ac' },
      pop.max_hl && { subTitle: ' max observed heteroplasmy', valueField: 'max_hl' },
    ].filter(d => d)),
  },
]

const getValueDisplay = (pop, valueField, precision) => (valueField === 'ac' ?
  `${pop.ac} out of ${pop.an}` : `${pop[valueField].toPrecision(precision || 2)}`)

const Frequencies = React.memo(({ variant }) => {
  const { populations = {}, svType } = variant
  const callsetHetPop = populations.callset_heteroplasmy || populations.seqr_heteroplasmy
  const isMito = callsetHetPop && callsetHetPop.af !== null && callsetHetPop.af !== undefined
  const popConfigs = isMito ? MITO_POPULATIONS : POPULATIONS
  let datasetType = isMito ? DATASET_TYPE_MITO_CALLS : DATASET_TYPE_SNV_INDEL_CALLS
  datasetType = svType ? DATASET_TYPE_SV_CALLS : datasetType
  const seqrAcSection = {
    name: 'seqr Global ACs',
    details: populations[SEQR_POP.field] ? [<GlobalAcPopup datasetType={datasetType} />].filter(s => s) : [],
  }
  const sections = [seqrAcSection, ...(isMito ? MITO_DETAIL_SECTIONS : DETAIL_SECTIONS).reduce(
    (acc, section) => ([
      ...acc,
      {
        name: section.name,
        details: popConfigs.map(popConfig => (section.hasDetail(populations[popConfig.field]) &&
          (!popConfig.section || popConfig.section === section.name) &&
          section.display(populations[popConfig.field]).map(({ subTitle, valueField }) => (
            <Popup.Content key={`${section.name}${popConfig.field}${subTitle}`}>
              {`${popConfig.fieldTitle}${subTitle || ''}: ${
                getValueDisplay(populations[popConfig.field], valueField, popConfig.precision)}`}
            </Popup.Content>
          ))
        )).filter(d => d).reduce((displayAcc, d) => ([...displayAcc, ...d]), []),
      },
    ]), [],
  )].filter(section => section.details.length)

  const freqContent = (<div>{popConfigs.map(pop => <FreqSummary key={pop.field} variant={variant} {...pop} />)}</div>)

  const hasHelpMessagePops = popConfigs.filter(
    pop => pop.helpMessage && populations[pop.field] && populations[pop.field].af !== null,
  )

  return (
    (hasHelpMessagePops.length || sections.length) ? (
      <Popup position="top center" wide="very" trigger={freqContent}>
        {sections.reduce((acc, { name, details }, i) => ([
          ...acc,
          (i > 0) && <VerticalSpacer key={name} height={5} />,
          <Popup.Header key={`${name}_header`} content={name} />,
          ...details,
        ]
        ), [])}
        {hasHelpMessagePops.map(pop => (
          <Popup.Content key={pop.field}>
            <Divider />
            <i>
              {pop.helpMessage}
            </i>
          </Popup.Content>
        ))}
      </Popup>
    ) : freqContent
  )
})

Frequencies.propTypes = {
  variant: PropTypes.object,
}

export default Frequencies

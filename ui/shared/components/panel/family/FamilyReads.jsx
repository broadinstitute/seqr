import React from 'react'
import ReactDOMServer from 'react-dom/server'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Segment, Icon, Popup, Divider, Loader } from 'semantic-ui-react'

import {
  getSortedIndividualsByFamily,
  getIGVSamplesByFamilySampleIndividual,
  getFamiliesByGuid,
  getProjectsByGuid,
  getGenesById,
  getSpliceOutliersByChromFamily,
} from 'redux/selectors'
import PedigreeIcon from '../../icons/PedigreeIcon'
import { CheckboxGroup, RadioGroup } from '../../form/Inputs'
import StateChangeForm from '../../form/StateChangeForm'
import { ButtonLink, HelpIcon } from '../../StyledComponents'
import { VerticalSpacer } from '../../Spacers'
import { getLocus, getOverlappedSpliceOutliers } from '../variants/VariantUtils'
import { AFFECTED, GENOME_VERSION_38, getVariantMainGeneId, RNASEQ_JUNCTION_PADDING } from '../../../utils/constants'
import {
  ALIGNMENT_TYPE, COVERAGE_TYPE, GCNV_TYPE, JUNCTION_TYPE, BUTTON_PROPS, TRACK_OPTIONS,
  MAPPABILITY_TRACK_OPTIONS, BAM_TRACK_OPTIONS,
  DNA_TRACK_TYPE_OPTIONS, RNA_TRACK_TYPE_OPTIONS, IGV_OPTIONS, REFERENCE_LOOKUP, RNA_TRACK_TYPE_LOOKUP,
  JUNCTION_TRACK_FIELDS, NORM_GTEX_TRACK_OPTIONS, AGG_GTEX_TRACK_OPTIONS,
} from './constants'

const IGV = React.lazy(() => import('../../graph/IGV'))

const MIN_LOCUS_RANGE_SIZE = 100

const getTrackOptions = (type, sample, individual) => {
  const name = ReactDOMServer.renderToString(
    <span id={`${individual.displayName}-${type}`}>
      <PedigreeIcon sex={individual.sex} affected={individual.affected} />
      {individual.displayName}
    </span>,
  )

  const url = `/api/project/${sample.projectGuid}/igv_track/${encodeURIComponent(sample.filePath)}`

  return { url, name, type, ...TRACK_OPTIONS[type] }
}

const getSampleColor = individual => (individual.affected === AFFECTED ? 'red' : 'blue')

const getIgvTracks = (igvSampleIndividuals, sortedIndividuals, sampleTypes) => {
  const gcnvSamplesByBatch = Object.entries(igvSampleIndividuals[GCNV_TYPE] || {}).reduce(
    (acc, [individualGuid, { filePath, sampleId }]) => {
      if (!acc[filePath]) {
        acc[filePath] = {}
      }
      acc[filePath][individualGuid] = sampleId
      return acc
    }, {},
  )

  const getIndivSampleType =
    (type, individualGuid) => sampleTypes.includes(type) && (igvSampleIndividuals[type] || {})[individualGuid]

  return Object.entries(igvSampleIndividuals).reduce((acc, [type, samplesByIndividual]) => (
    sampleTypes.includes(type) ? [
      ...acc,
      ...sortedIndividuals.map((individual) => {
        const { individualGuid } = individual
        const sample = samplesByIndividual[individualGuid]
        if (!sample) {
          return null
        }

        const track = getTrackOptions(type, sample, individual)

        if (type === ALIGNMENT_TYPE) {
          if (sample.filePath.endsWith('.cram')) {
            Object.assign(track, {
              format: 'cram',
              indexURL: `${track.url}.crai`,
            })
          } else {
            Object.assign(track, BAM_TRACK_OPTIONS)
          }
        } else if (type === JUNCTION_TYPE) {
          track.indexURL = `${track.url}.tbi`

          const coverageSample = getIndivSampleType(COVERAGE_TYPE, individualGuid)
          if (coverageSample) {
            const coverageTrack = getTrackOptions(COVERAGE_TYPE, coverageSample, individual)
            return {
              type: 'merged',
              name: track.name,
              height: track.height,
              tracks: [coverageTrack, track],
            }
          }
        } else if (type === COVERAGE_TYPE && getIndivSampleType(JUNCTION_TYPE, individualGuid)) {
          return null
        } else if (type === GCNV_TYPE) {
          const batch = gcnvSamplesByBatch[sample.filePath]
          const individualGuids = Object.keys(batch).sort()
          if (individualGuids[0] !== individualGuid) {
            return null
          }

          const batchIndividuals = sortedIndividuals.filter(indiv => !!batch[indiv.individualGuid])
          return {
            ...track,
            indexURL: `${track.url}.tbi`,
            highlightSamples: batchIndividuals.reduce((higlightAcc, indiv) => ({
              [batch[indiv.individualGuid] || indiv.individualId]: getSampleColor(indiv),
              ...higlightAcc,
            }), {}),
            name: individualGuids.length === 1 ? track.name : batchIndividuals.map(
              ({ displayName }) => displayName,
            ).join(', '),
          }
        }

        return track
      }),
    ] : acc
  ), []).filter(track => track)
}

const ShowIgvButton = ({ type, showReads, ...props }) => (BUTTON_PROPS[type] ? (
  <ButtonLink
    padding="0 0 0 1em"
    onClick={showReads && showReads(type === JUNCTION_TYPE ? [JUNCTION_TYPE, COVERAGE_TYPE] : [type])}
    {...BUTTON_PROPS[type]}
    {...props}
  />
) : null)

ShowIgvButton.propTypes = {
  type: PropTypes.string,
  familyGuid: PropTypes.string,
  showReads: PropTypes.func,
}

const ReadButtons = React.memo((
  { variant, familyGuid, igvSamplesByFamilySampleIndividual, familiesByGuid, buttonProps, showReads },
) => {
  const familyGuids = variant ? variant.familyGuids : [familyGuid]

  const sampleTypeFamilies = familyGuids.reduce(
    (acc, fGuid) => {
      Object.keys((igvSamplesByFamilySampleIndividual || {})[fGuid] || {}).forEach((type) => {
        if (!acc[type]) {
          acc[type] = []
        }
        acc[type].push(fGuid)
      })
      return acc
    }, {},
  )

  if (!Object.keys(sampleTypeFamilies).length) {
    return null
  }

  if (familyGuids.length === 1) {
    return Object.keys(sampleTypeFamilies).map(
      type => <ShowIgvButton key={type} type={type} {...buttonProps} showReads={showReads(familyGuids[0])} />,
    )
  }

  return Object.entries(sampleTypeFamilies).reduce((acc, [type, fGuids]) => ([
    ...acc,
    <ShowIgvButton key={type} type={type} {...buttonProps} />,
    ...fGuids.map(fGuid => (
      <ShowIgvButton
        key={`${fGuid}-${type}`}
        content={`| ${familiesByGuid[fGuid].familyId}`}
        icon={null}
        type={type}
        showReads={showReads(fGuid)}
        padding="0"
      />
    )),
  ]), [])
})

ReadButtons.propTypes = {
  variant: PropTypes.object,
  familyGuid: PropTypes.string,
  buttonProps: PropTypes.object,
  familiesByGuid: PropTypes.object,
  igvSamplesByFamilySampleIndividual: PropTypes.object,
  showReads: PropTypes.func,
}

const applyUserTrackSettings = (tracks, options) => tracks.map(track => ({
  ...options[track.type] ? { ...track, ...options[track.type] } : track,
  ...(track.type === 'merged') ? {
    tracks: track.tracks.map(tr => (options[tr.type] ? { ...tr, ...options[tr.type] } : tr)),
  } : {},
}))

const getVariantLocus = (variant, project) => {
  const size = variant.end && variant.end - variant.pos
  return getLocus(
    variant.chrom,
    (variant.genomeVersion !== project.genomeVersion && variant.liftedOverPos) ? variant.liftedOverPos : variant.pos,
    size ? Math.max(Math.round(size / 2), MIN_LOCUS_RANGE_SIZE) : MIN_LOCUS_RANGE_SIZE,
    size,
  )
}

const getGeneLocus = (variant, genesById, project) => {
  const gene = genesById[getVariantMainGeneId(variant)]
  if (gene) {
    const genomeVersion = (project.genomeVersion === GENOME_VERSION_38) ? 'Grch38' : 'Grch37'
    const size = gene[`codingRegionSize${genomeVersion}`]
    return getLocus(gene[`chrom${genomeVersion}`], gene[`start${genomeVersion}`],
      size ? Math.max(Math.round(size / 3), MIN_LOCUS_RANGE_SIZE) : MIN_LOCUS_RANGE_SIZE,
      size)
  }
  return null
}

const IgvPanel = React.memo((
  { igvSampleIndividuals, sortedIndividuals, project, sampleTypes, rnaReferences, junctionTrackOptions, locus },
) => {
  const tracks = applyUserTrackSettings(
    rnaReferences.concat(getIgvTracks(igvSampleIndividuals, sortedIndividuals, sampleTypes)),
    { [JUNCTION_TYPE]: junctionTrackOptions },
  )

  return (
    <React.Suspense fallback={<Loader />}>
      <IGV tracks={tracks} reference={REFERENCE_LOOKUP[project.genomeVersion]} locus={locus} {...IGV_OPTIONS} />
    </React.Suspense>
  )
})

IgvPanel.propTypes = {
  sampleTypes: PropTypes.arrayOf(PropTypes.string),
  rnaReferences: PropTypes.arrayOf(PropTypes.object),
  junctionTrackOptions: PropTypes.object,
  sortedIndividuals: PropTypes.arrayOf(PropTypes.object),
  igvSampleIndividuals: PropTypes.object,
  project: PropTypes.object,
  locus: PropTypes.string,
}

const TISSUE_REFERENCE_KEY = {
  WB: 'Blood',
  F: 'Fibs',
  M: 'Muscle',
  L: 'Lymph',
}

const TISSUE_REFERENCES_LOOKUP = Object.entries(TISSUE_REFERENCE_KEY).reduce((acc, [tissueType, key]) => ({
  ...acc,
  [tissueType]: [...NORM_GTEX_TRACK_OPTIONS, ...AGG_GTEX_TRACK_OPTIONS].filter(track => track.text.includes(key))
    .map(track => track.value),
}), {})

const getSpliceOutlierLocus = (variant, spliceOutliersByFamily) => {
  const overlappedOutliers = getOverlappedSpliceOutliers(variant, spliceOutliersByFamily)
  if (overlappedOutliers.length < 1) {
    return null
  }
  const { chrom } = variant
  const minPos = Math.min(...overlappedOutliers.map(outlier => outlier.start))
  const maxEnd = Math.max(...overlappedOutliers.map(outlier => outlier.end))
  return getLocus(chrom, minPos, RNASEQ_JUNCTION_PADDING, maxEnd - minPos)
}

class FamilyReads extends React.PureComponent {

  static propTypes = {
    variant: PropTypes.object,
    layout: PropTypes.elementType,
    familyGuid: PropTypes.string,
    buttonProps: PropTypes.object,
    projectsByGuid: PropTypes.object,
    familiesByGuid: PropTypes.object,
    sortedIndividualByFamily: PropTypes.object,
    igvSamplesByFamilySampleIndividual: PropTypes.object,
    genesById: PropTypes.object,
    noTriggerButton: PropTypes.bool,
    spliceOutliersByFamily: PropTypes.object,
  }

  state = {
    openFamily: null,
    sampleTypes: [],
    rnaReferences: [],
    junctionTrackOptions: {
      minJunctionEndsVisible: 0,
      minUniquelyMappedReads: 0,
      minTotalReads: 0,
    },
    locus: null,
  }

  updateReads = (familyGuid, locus, sampleTypes, tissueType) => {
    this.setState({ openFamily: familyGuid, sampleTypes, locus, rnaReferences: TISSUE_REFERENCES_LOOKUP[tissueType] })
  }

  getProjectForFamily = (familyGuid) => {
    const { projectsByGuid, familiesByGuid } = this.props
    return projectsByGuid[familiesByGuid[familyGuid].projectGuid]
  }

  showReads = familyGuid => sampleTypes => () => {
    const { variant } = this.props
    this.setState({
      openFamily: familyGuid,
      sampleTypes,
      locus: variant && getVariantLocus(variant, this.getProjectForFamily(familyGuid)),
    })
  }

  hideReads = () => {
    this.setState({
      openFamily: null,
      sampleTypes: [],
      rnaReferences: [],
    })
  }

  updateSampleTypes = (sampleTypes) => {
    if (sampleTypes.some(sampleType => RNA_TRACK_TYPE_LOOKUP.has(sampleType))) {
      this.setState({
        sampleTypes,
      })
    } else {
      this.setState({
        sampleTypes,
        rnaReferences: [],
      })
    }
  }

  updateRnaReferences = (rnaReferences) => {
    this.setState({
      rnaReferences,
    })
  }

  junctionsOptionChange = field => (value) => {
    this.setState(prevState => (
      { junctionTrackOptions: { ...prevState.junctionTrackOptions, [field]: value } }
    ))
  }

  locusChange = (locus) => {
    this.setState({ locus })
  }

  gtexSelector = (typeLabel, options) => {
    const { rnaReferences } = this.state
    return (
      <CheckboxGroup
        groupLabel={
          <label>
            {`${typeLabel} GTEx Tracks`}
            <Popup
              trigger={<HelpIcon color="black" />}
              content="Normalized GTEx tracks are more comparable to patient RNA-seq data. If you want to explore if a splice junction is seen in any sample, aggregate GTEx tracks show all data. The y-axis range is expected to differ between a single patient sample and normalized or aggregate GTEx data."
              size="small"
              position="top center"
            />
          </label>
        }
        value={rnaReferences}
        options={options}
        onChange={this.updateRnaReferences}
      />
    )
  }

  getSampleColorPanel = () => {
    const { openFamily } = this.state
    const { igvSamplesByFamilySampleIndividual, sortedIndividualByFamily } = this.props

    const gcnvSampleIndividuals = ((igvSamplesByFamilySampleIndividual || {})[openFamily] || {})[GCNV_TYPE]
    if (!gcnvSampleIndividuals || !sortedIndividualByFamily[openFamily]) {
      return null
    }

    return sortedIndividualByFamily[openFamily].filter(
      ({ individualGuid }) => !!gcnvSampleIndividuals[individualGuid],
    ).map(individual => (
      <div key={individual.individualGuid}>
        <Icon name="square full" color={getSampleColor(individual)} />
        <label>{individual.displayName}</label>
      </div>
    ))
  }

  render() {
    const {
      variant, familyGuid, buttonProps, layout, igvSamplesByFamilySampleIndividual, familiesByGuid,
      projectsByGuid, genesById, sortedIndividualByFamily, noTriggerButton, spliceOutliersByFamily, ...props
    } = this.props
    const { openFamily, sampleTypes, rnaReferences, junctionTrackOptions, locus } = this.state

    const showReads = noTriggerButton ? null : (
      <ReadButtons
        variant={variant}
        familyGuid={familyGuid}
        buttonProps={buttonProps}
        igvSamplesByFamilySampleIndividual={igvSamplesByFamilySampleIndividual}
        familiesByGuid={familiesByGuid}
        showReads={this.showReads}
      />
    )

    const igvSampleIndividuals = (
      openFamily && (igvSamplesByFamilySampleIndividual || {})[openFamily]) || {}
    const dnaTrackOptions = DNA_TRACK_TYPE_OPTIONS.filter(({ value }) => igvSampleIndividuals[value])
    const rnaTrackOptions = RNA_TRACK_TYPE_OPTIONS.filter(({ value }) => igvSampleIndividuals[value])
    const project = openFamily && this.getProjectForFamily(openFamily)
    const geneLocus = project && variant && getGeneLocus(variant, genesById, project)
    const locusOptions = [
      { text: 'Variant', value: geneLocus && getVariantLocus(variant, project) },
      { text: 'Gene', value: geneLocus },
      {
        text: 'Splice Outlier',
        value: variant && getSpliceOutlierLocus({ ...variant, familyGuids: [openFamily] }, spliceOutliersByFamily),
      },
    ].filter(({ value }) => value)
    const reads = Object.keys(igvSampleIndividuals).length > 0 ? (
      <Segment.Group horizontal>
        {(dnaTrackOptions.length > 1 || rnaTrackOptions.length > 0) && (
          <Segment>
            {dnaTrackOptions.length > 0 && (
              <CheckboxGroup
                groupLabel="DNA Tracks"
                value={sampleTypes}
                options={dnaTrackOptions}
                onChange={this.updateSampleTypes}
              />
            )}
            {rnaTrackOptions.length > 0 && (
              <CheckboxGroup
                groupLabel="RNA Tracks"
                value={sampleTypes}
                options={rnaTrackOptions}
                onChange={this.updateSampleTypes}
              />
            )}
            {sampleTypes.includes(GCNV_TYPE) && (
              <div>
                <Divider horizontal>gCNV Samples</Divider>
                {this.getSampleColorPanel()}
              </div>
            )}
            { locusOptions.length > 0 && (
              <div>
                <Divider horizontal>Range</Divider>
                <RadioGroup
                  value={locus}
                  options={locusOptions}
                  onChange={this.locusChange}
                />
              </div>
            )}
            {rnaTrackOptions.length > 0 && (
              <div>
                {sampleTypes.some(sampleType => RNA_TRACK_TYPE_LOOKUP.has(sampleType)) && (
                  <div>
                    <Divider horizontal>Reference Tracks</Divider>
                    {this.gtexSelector('Normalized', NORM_GTEX_TRACK_OPTIONS)}
                    {this.gtexSelector('Aggregate', AGG_GTEX_TRACK_OPTIONS)}
                    <CheckboxGroup
                      groupLabel="Mappability Tracks"
                      value={rnaReferences}
                      options={MAPPABILITY_TRACK_OPTIONS}
                      onChange={this.updateRnaReferences}
                    />
                    <Divider horizontal>Junction Filters</Divider>
                    <StateChangeForm
                      fields={JUNCTION_TRACK_FIELDS}
                      initialValues={junctionTrackOptions}
                      updateField={this.junctionsOptionChange}
                    />
                  </div>
                )}
              </div>
            )}
          </Segment>
        )}
        <Segment>
          <ButtonLink onClick={this.hideReads} icon={<Icon name="remove" color="grey" />} floated="right" size="large" />
          <VerticalSpacer height={20} />
          <IgvPanel
            igvSampleIndividuals={igvSampleIndividuals}
            sampleTypes={sampleTypes}
            rnaReferences={rnaReferences}
            junctionTrackOptions={junctionTrackOptions}
            sortedIndividuals={sortedIndividualByFamily[openFamily]}
            project={project}
            locus={locus}
          />
        </Segment>
      </Segment.Group>
    ) : null

    return React.createElement(layout, { variant, reads, showReads, updateReads: this.updateReads, ...props })
  }

}

const mapStateToProps = (state, ownProps) => ({
  igvSamplesByFamilySampleIndividual: getIGVSamplesByFamilySampleIndividual(state),
  sortedIndividualByFamily: getSortedIndividualsByFamily(state),
  familiesByGuid: getFamiliesByGuid(state),
  projectsByGuid: getProjectsByGuid(state),
  genesById: getGenesById(state),
  spliceOutliersByFamily: ownProps.variant && getSpliceOutliersByChromFamily(state)[ownProps.variant.chrom],
})

export default connect(mapStateToProps)(FamilyReads)

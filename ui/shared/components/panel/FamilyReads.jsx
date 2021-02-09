import React from 'react'
import ReactDOMServer from 'react-dom/server'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Segment, Icon } from 'semantic-ui-react'

import {
  getIndividualsByGuid,
  getIGVSamplesByFamilySampleIndividual,
  getFamiliesByGuid,
  getProjectsByGuid,
} from 'redux/selectors'
import PedigreeIcon from '../icons/PedigreeIcon'
import IGV from '../graph/IGV'
import { ButtonLink } from '../StyledComponents'
import { VerticalSpacer } from '../Spacers'
import { getLocus } from './variants/Annotations'
import { AFFECTED, GENOME_VERSION_DISPLAY_LOOKUP, GENOME_VERSION_LOOKUP, GENOME_VERSION_38 } from '../../utils/constants'

const ALIGNMENT_TYPE = 'alignment'
const COVERAGE_TYPE = 'wig'
const JUNCTION_TYPE = 'spliceJunctions'
const GCNV_TYPE = 'gcnv'


const ALIGNMENT_TRACK_OPTIONS = {
  alignmentShading: 'strand',
  format: 'cram',
  showSoftClips: true,
}

const CRAM_PROXY_TRACK_OPTIONS = {
  sourceType: 'pysam',
  alignmentFile: '/placeholder.cram',
  referenceFile: '/placeholder.fa',
}

const BAM_TRACK_OPTIONS = {
  indexed: true,
  format: 'bam',
}

const COVERAGE_TRACK_OPTIONS = {
  format: 'bigwig',
  height: 170,
}

const JUNCTION_TRACK_OPTIONS = {
  format: 'bed',
  height: 170,
  minUniquelyMappedReads: 0,
  minTotalReads: 1,
  maxFractionMultiMappedReads: 1,
  minSplicedAlignmentOverhang: 0,
  colorBy: 'isAnnotatedJunction',
  labelUniqueReadCount: true,
}

const GCNV_TRACK_OPTIONS = {
  format: 'gcnv',
  height: 200,
  min: 0,
  max: 5,
  autoscale: true,
  onlyHandleClicksForHighlightedSamples: true,
}

const TRACK_OPTIONS = {
  [ALIGNMENT_TYPE]: ALIGNMENT_TRACK_OPTIONS,
  [COVERAGE_TYPE]: COVERAGE_TRACK_OPTIONS,
  [JUNCTION_TYPE]: JUNCTION_TRACK_OPTIONS,
  [GCNV_TYPE]: GCNV_TRACK_OPTIONS,
}

const BUTTON_PROPS = {
  [ALIGNMENT_TYPE]: { icon: 'options', content: 'SHOW READS' },
  [JUNCTION_TYPE]: { icon: 'dna rotated', content: 'SHOW RNASeq' },
  [GCNV_TYPE]: { icon: 'industry', content: 'SHOW gCNV' },
}

const IGV_OPTIONS = {
  showKaryo: false,
  showIdeogram: true,
  showNavigation: true,
  showRuler: true,
  showCenterGuide: true,
  showCursorTrackingGuide: true,
  showCommandBar: true,
}

const getTrackOptions = (type, sample, individual) => {
  const name = ReactDOMServer.renderToString(
    <span><PedigreeIcon sex={individual.sex} affected={individual.affected} />{individual.displayName}</span>,
  )

  const url = `/api/project/${sample.projectGuid}/igv_track/${encodeURIComponent(sample.filePath)}`

  return { url, name, type, ...TRACK_OPTIONS[type] }
}

const getIgvTracks = (variant, igvSampleIndividuals, individualsByGuid, sampleTypes) => {
  const gcnvSamplesByBatch = Object.entries(igvSampleIndividuals[GCNV_TYPE] || {}).reduce(
    (acc, [individualGuid, { filePath, sampleId }]) => {
      if (!acc[filePath]) {
        acc[filePath] = {}
      }
      acc[filePath][individualGuid] = sampleId
      return acc
    }, {})

  return Object.entries(igvSampleIndividuals).reduce((acc, [type, samplesByIndividual]) => (
    sampleTypes.includes(type) ? [
      ...acc,
      ...Object.entries(samplesByIndividual).map(([individualGuid, sample]) => {
        const individual = individualsByGuid[individualGuid]
        const track = getTrackOptions(type, sample, individual)

        if (type === ALIGNMENT_TYPE) {
          if (sample.filePath.endsWith('.cram')) {
            if (sample.filePath.startsWith('gs://')) {
              Object.assign(track, {
                format: 'cram',
                indexURL: `${track.url}.crai`,
              })
            } else {
              Object.assign(track, CRAM_PROXY_TRACK_OPTIONS)
            }
          } else {
            Object.assign(track, BAM_TRACK_OPTIONS)
          }
        } else if (type === JUNCTION_TYPE) {
          track.indexURL = `${track.url}.tbi`

          const coverageSample = (igvSampleIndividuals[COVERAGE_TYPE] || {})[individualGuid]
          if (coverageSample) {
            const coverageTrack = getTrackOptions(COVERAGE_TYPE, coverageSample, individual)
            return {
              type: 'merged',
              name: track.name,
              height: track.height,
              tracks: [coverageTrack, track],
            }
          }
        } else if (type === COVERAGE_TYPE && (igvSampleIndividuals[JUNCTION_TYPE] || {})[individualGuid]) {
          return null
        } else if (type === GCNV_TYPE) {
          const batch = gcnvSamplesByBatch[sample.filePath]
          const individualGuids = Object.keys(batch).sort()

          return individualGuids[0] === individualGuid ? {
            ...track,
            indexURL: `${track.url}.tbi`,
            highlightSamples: Object.entries(batch).reduce((higlightAcc, [iGuid, sampleId]) => ({
              [sampleId || individualsByGuid[iGuid].individualId]:
                individualsByGuid[iGuid].affected === AFFECTED ? 'red' : 'blue',
              ...higlightAcc,
            }), {}),
            name: individualGuids.length === 1 ? track.name : individualGuids.map(
              iGuid => individualsByGuid[iGuid].displayName).join(', '),
          } : null
        }

        return track
      }),
    ] : acc
  ), []).filter(track => track)
}

const ShowIgvButton = ({ type, showReads, ...props }) => (BUTTON_PROPS[type] ?
  <ButtonLink
    padding="0 0 0 1em"
    onClick={showReads && showReads(type === JUNCTION_TYPE ? [JUNCTION_TYPE, COVERAGE_TYPE] : [type])}
    {...BUTTON_PROPS[type]}
    {...props}
  /> : null
)

ShowIgvButton.propTypes = {
  type: PropTypes.string,
  familyGuid: PropTypes.string,
  showReads: PropTypes.func,
}

const BaseReadButtons = React.memo(({ variant, familyGuid, igvSamplesByFamilySampleIndividual, familiesByGuid, buttonProps, showReads }) => {
  const familyGuids = variant ? variant.familyGuids : [familyGuid]

  const sampleTypeFamilies = familyGuids.reduce(
    (acc, fGuid) => {
      Object.keys(igvSamplesByFamilySampleIndividual[fGuid] || {}).forEach((type) => {
        if (!acc[type]) {
          acc[type] = []
        }
        acc[type].push(fGuid)
      })
      return acc
    }, {})

  if (!Object.keys(sampleTypeFamilies).length) {
    return null
  }

  if (familyGuids.length === 1) {
    return Object.keys(sampleTypeFamilies).map(type =>
      <ShowIgvButton key={type} type={type} {...buttonProps} showReads={showReads(familyGuids[0])} />,
    )
  }

  return Object.entries(sampleTypeFamilies).reduce((acc, [type, fGuids]) => ([
    ...acc,
    <ShowIgvButton key={type} type={type} {...buttonProps} />,
    ...fGuids.map(fGuid =>
      <ShowIgvButton
        key={`${fGuid}-${type}`}
        content={`| ${familiesByGuid[fGuid].familyId}`}
        icon={null}
        type={type}
        showReads={showReads(fGuid)}
        padding="0"
      />,
    ),
  ]), [])

})

BaseReadButtons.propTypes = {
  variant: PropTypes.object,
  familyGuid: PropTypes.string,
  buttonProps: PropTypes.object,
  familiesByGuid: PropTypes.object,
  igvSamplesByFamilySampleIndividual: PropTypes.object,
  showReads: PropTypes.func,
}

const mapButtonStateToProps = state => ({
  igvSamplesByFamilySampleIndividual: getIGVSamplesByFamilySampleIndividual(state),
  familiesByGuid: getFamiliesByGuid(state),
})

const ReadButtons = connect(mapButtonStateToProps)(BaseReadButtons)


const BaseIgvPanel = React.memo(({ variant, igvSampleIndividuals, individualsByGuid, project, hideReads, sampleTypes }) => {
  const genomeBuild = GENOME_VERSION_LOOKUP[project.genomeVersion]
  const genomeDisplay = GENOME_VERSION_DISPLAY_LOOKUP[genomeBuild]

  const locus = variant && getLocus(
    variant.chrom,
    (variant.genomeVersion !== project.genomeVersion && variant.liftedOverPos) ? variant.liftedOverPos : variant.pos,
    100,
  )

  const tracks = getIgvTracks(variant, igvSampleIndividuals, individualsByGuid, sampleTypes)
  tracks.push({
    url: `https://storage.googleapis.com/seqr-reference-data/${genomeBuild}/gencode/gencode.v27${project.genomeVersion === GENOME_VERSION_38 ? '' : 'lift37'}.annotation.sorted.gtf.gz`,
    name: `gencode ${genomeDisplay}v27`,
    displayMode: 'SQUISHED',
  })

  return (
    <Segment>
      <ButtonLink onClick={hideReads} icon={<Icon name="remove" color="grey" />} floated="right" size="large" />
      <VerticalSpacer height={20} />
      <IGV tracks={tracks} genome={genomeDisplay} locus={locus} {...IGV_OPTIONS} />
    </Segment>
  )
})

BaseIgvPanel.propTypes = {
  variant: PropTypes.object,
  sampleTypes: PropTypes.array,
  individualsByGuid: PropTypes.object,
  igvSampleIndividuals: PropTypes.object,
  project: PropTypes.object,
  hideReads: PropTypes.func,
}

const mapPanelStateToProps = (state, ownProps) => ({
  igvSampleIndividuals: getIGVSamplesByFamilySampleIndividual(state)[ownProps.openFamily],
  individualsByGuid: getIndividualsByGuid(state),
  project: getProjectsByGuid(state)[getFamiliesByGuid(state)[ownProps.openFamily].projectGuid],
})

const IgvPanel = connect(mapPanelStateToProps)(BaseIgvPanel)

class FamilyReads extends React.PureComponent {

  static propTypes = {
    variant: PropTypes.object,
    layout: PropTypes.any,
    familyGuid: PropTypes.string,
    buttonProps: PropTypes.object,
    familiesByGuid: PropTypes.object,
    individualsByGuid: PropTypes.object,
    igvSamplesByFamilySampleIndividual: PropTypes.object,
  }

  constructor(props) {
    super(props)
    this.state = {
      openFamily: null,
      sampleTypes: null,
    }
  }

  showReads = familyGuid => sampleTypes => () => {
    this.setState({
      openFamily: familyGuid,
      sampleTypes,
    })
  }

  hideReads = () => {
    this.setState({
      openFamily: null,
      sampleTypes: null,
    })
  }

  render() {
    const { variant, familyGuid, buttonProps, layout, ...props } = this.props

    const showReads = <ReadButtons
      variant={variant}
      familyGuid={familyGuid}
      buttonProps={buttonProps}
      showReads={this.showReads}
    />

    const reads = this.state.openFamily ?
      <IgvPanel variant={variant} hideReads={this.hideReads} {...this.state} /> : null

    return React.createElement(layout, { variant, reads, showReads, ...props })
  }
}

export default FamilyReads

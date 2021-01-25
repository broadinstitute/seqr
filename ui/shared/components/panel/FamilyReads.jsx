import React from 'react'
import ReactDOMServer from 'react-dom/server'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Segment, Icon } from 'semantic-ui-react'

import { getIndividualsByGuid, getIGVSamplesByFamily, getFamiliesByGuid } from 'redux/selectors'
import PedigreeIcon from '../icons/PedigreeIcon'
import IGV from '../graph/IGV'
import { ButtonLink } from '../StyledComponents'
import { VerticalSpacer } from '../Spacers'
import { getLocus } from './variants/Annotations'
import { AFFECTED } from '../../utils/constants'

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

const getIgvOptions = (variant, igvSamples, individualsByGuid) => {
  // const igvTracksBySampleIndividual = igvSamples.reduce((acc, sample) => {
  const igvTracksBySampleIndividual = [
    ...igvSamples,
    { ...igvSamples[0], filePath: 'gs://macarthurlab-rnaseq/batch_0/junctions_bed_for_igv_js/250DV_LR_M1.junctions.bed.gz', sampleType: JUNCTION_TYPE },
    { ...igvSamples[0], filePath: 'gs://macarthurlab-rnaseq/batch_0/bigWig/250DV_LR_M1.bigWig', sampleType: COVERAGE_TYPE },
    { ...igvSamples[0], filePath: 'gs://seqr-datasets-gcnv/GRCh38/RDG_WES_Broad_Internal/v1/beds/cc_20_1.dcr.bed.gz', sampleType: GCNV_TYPE, sampleId: 'C1847_MAAC019_v1_Exome_GCP' },
    { ...igvSamples[1], filePath: 'gs://seqr-datasets-gcnv/GRCh38/RDG_WES_Broad_Internal/v1/beds/cc_20_1.dcr.bed.gz', sampleType: GCNV_TYPE, sampleId: 'C1847_MCOP047_v1_Exome_GCP' },
  ].reduce((acc, sample) => {
    const type = sample.sampleType || ALIGNMENT_TYPE // TODO add to model

    const individual = individualsByGuid[sample.individualGuid]
    const trackName = ReactDOMServer.renderToString(
      <span><PedigreeIcon sex={individual.sex} affected={individual.affected} />{individual.displayName}</span>,
    )

    const url = `/api/project/${sample.projectGuid}/igv_track/${encodeURIComponent(sample.filePath)}`

    const trackOptions = { type, ...TRACK_OPTIONS[type] }

    if (type === ALIGNMENT_TYPE) {
      if (sample.filePath.endsWith('.cram')) {
        if (sample.filePath.startsWith('gs://')) {
          Object.assign(trackOptions, {
            format: 'cram',
            indexURL: `${url}.crai`,
          })
        } else {
          Object.assign(trackOptions, CRAM_PROXY_TRACK_OPTIONS)
        }
      } else {
        Object.assign(trackOptions, BAM_TRACK_OPTIONS)
      }
    } else if (type === JUNCTION_TYPE) {
      trackOptions.indexURL = `${url}.tbi`
    } else if (type === GCNV_TYPE) {
      trackOptions.indexURL = `${url}.tbi`
      trackOptions.highlightSamples = { [sample.sampleId]: individual.affected === AFFECTED ? 'red' : 'blue' } // TODO add sampleId to model
    }

    if (!acc[type]) {
      acc[type] = {}
    }
    acc[type][sample.individualGuid] = {
      url,
      name: trackName,
      ...trackOptions,
    }
    return acc
  }, {})

  const gcnvSamplesByBatch = Object.entries(igvTracksBySampleIndividual[GCNV_TYPE] || {}).reduce(
    (acc, [individualGuid, { url, highlightSamples }]) => {
      if (!acc[url]) {
        acc[url] = { individualGuid, highlightSamples }
      } else {
        acc[url].highlightSamples = { ...acc[url].highlightSamples, ...highlightSamples }
      }
      return acc
    }, {})

  const igvTracks = Object.values(igvTracksBySampleIndividual).reduce((acc, tracksByIndividual) => ([
    ...acc,
    ...Object.entries(tracksByIndividual).map(([individualGuid, track]) => {
      if (track.type === JUNCTION_TYPE) {
        const coverageTrack = igvTracksBySampleIndividual[COVERAGE_TYPE][individualGuid]
        if (coverageTrack) {
          return {
            type: 'merged',
            name: track.name,
            height: track.height,
            tracks: [coverageTrack, track],
          }
        }
      } else if (track.type === COVERAGE_TYPE && igvTracksBySampleIndividual[JUNCTION_TYPE][individualGuid]) {
        return null
      } else if (track.type === GCNV_TYPE) {
        const batch = gcnvSamplesByBatch[track.url]
        return batch.individualGuid === individualGuid ? { ...track, highlightSamples: batch.highlightSamples } : null
      }

      return track
    }),
  ]), []).filter(track => track)

  // TODO better determiner of genome version?
  const isBuild38 = igvSamples.some(sample => sample.filePath.endsWith('.cram'))
  const genome = isBuild38 ? 'hg38' : 'hg19'

  const locus = variant && getLocus(
    variant.chrom, (!isBuild38 && variant.liftedOverPos) ? variant.liftedOverPos : variant.pos, 100,
  )

  igvTracks.push({
    url: `https://storage.googleapis.com/seqr-reference-data/${isBuild38 ? 'GRCh38' : 'GRCh37'}/gencode/gencode.v27${isBuild38 ? '' : 'lift37'}.annotation.sorted.gtf.gz`,
    name: `gencode ${genome}v27`,
    displayMode: 'SQUISHED',
  })

  return {
    locus,
    tracks: igvTracks,
    genome,
    showKaryo: false,
    showIdeogram: true,
    showNavigation: true,
    showRuler: true,
    showCenterGuide: true,
    showCursorTrackingGuide: true,
    showCommandBar: true,
  }
}

const ReadIconButton = props => <ButtonLink icon="options" content="SHOW READS" {...props} />

const ReadButtons = React.memo(({ variant, familyGuid, igvSamplesByFamily, familiesByGuid, buttonProps, showReads }) => {
  const familyGuids = variant ? variant.familyGuids : [familyGuid]

  const familiesWithReads = familyGuids.filter(fGuid => (igvSamplesByFamily[fGuid] || []).length > 0)
  if (!familiesWithReads.length) {
    return null
  }

  if (familiesWithReads.length === 1) {
    return <ReadIconButton onClick={showReads(familiesWithReads[0])} {...buttonProps} />
  }

  return [
    <ReadIconButton key="showReads" {...buttonProps} />,
    ...familiesWithReads.map(fGuid => (
      <ButtonLink key={fGuid} content={`| ${familiesByGuid[fGuid].familyId}`} onClick={showReads(fGuid)} padding="0" />
    )),
  ]
})

ReadButtons.propTypes = {
  variant: PropTypes.object,
  familyGuid: PropTypes.string,
  buttonProps: PropTypes.object,
  familiesByGuid: PropTypes.object,
  igvSamplesByFamily: PropTypes.object,
  showReads: PropTypes.func,
}

const IgvPanel = React.memo(({ variant, igvSamples, individualsByGuid, hideReads }) => {
  const igvOptions = getIgvOptions(variant, igvSamples, individualsByGuid)
  return (
    <Segment>
      <ButtonLink onClick={hideReads} icon={<Icon name="remove" color="grey" />} floated="right" size="large" />
      <VerticalSpacer height={20} />
      <IGV igvOptions={igvOptions} />
    </Segment>
  )
})

IgvPanel.propTypes = {
  variant: PropTypes.object,
  individualsByGuid: PropTypes.object,
  igvSamples: PropTypes.array,
  hideReads: PropTypes.func,
}

class FamilyReads extends React.PureComponent {

  static propTypes = {
    variant: PropTypes.object,
    layout: PropTypes.any,
    familyGuid: PropTypes.string,
    buttonProps: PropTypes.object,
    familiesByGuid: PropTypes.object,
    individualsByGuid: PropTypes.object,
    igvSamplesByFamily: PropTypes.object,
  }

  constructor(props) {
    super(props)
    this.state = {
      openFamily: null,
    }
  }

  showReads = familyGuid => () => {
    this.setState({
      openFamily: familyGuid,
    })
  }

  hideReads = () => {
    this.setState({
      openFamily: null,
    })
  }

  render() {
    const {
      variant, familyGuid, buttonProps, layout, igvSamplesByFamily, individualsByGuid, familiesByGuid, ...props
    } = this.props

    const showReads = <ReadButtons
      variant={variant}
      familyGuid={familyGuid}
      buttonProps={buttonProps}
      igvSamplesByFamily={igvSamplesByFamily}
      familiesByGuid={familiesByGuid}
      showReads={this.showReads}
    />

    const igvSamples = this.state.openFamily && igvSamplesByFamily[this.state.openFamily]
    const reads = (igvSamples && igvSamples.length) ?
      <IgvPanel
        variant={variant}
        igvSamples={igvSamples}
        individualsByGuid={individualsByGuid}
        hideReads={this.hideReads}
      /> : null

    return React.createElement(layout, { variant, reads, showReads, ...props })
  }
}

const mapStateToProps = state => ({
  igvSamplesByFamily: getIGVSamplesByFamily(state),
  individualsByGuid: getIndividualsByGuid(state),
  familiesByGuid: getFamiliesByGuid(state),
})

export default connect(mapStateToProps)(FamilyReads)

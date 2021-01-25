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

const ALIGNMENT_TYPE = 'alignment'
const COVERAGE_TYPE = 'wig'
const JUNCTION_TYPE = 'spliceJunctions'


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
  // order: 11, // TODO
}

const JUNCTION_TRACK_OPTIONS = {
  format: 'bed',
  // order: 10, // TODO
  height: 170,
  minUniquelyMappedReads: 0,
  minTotalReads: 1,
  maxFractionMultiMappedReads: 1,
  minSplicedAlignmentOverhang: 0,
  thicknessBasedOn: 'numUniqueReads', //options: numUniqueReads (default), numReads, isAnnotatedJunction
  bounceHeightBasedOn: 'random', //options: random (default), distance, thickness
  colorBy: 'strand', //options: numUniqueReads (default), numReads, isAnnotatedJunction, strand, motif
  colorByNumReadsThreshold: 5, //!== undefined ? sjOptions.colorByNumReadsThreshold : SJ_DEFAULT_COLOR_BY_NUM_READS_THRESHOLD,
  hideStrand: undefined, //sjOptions.showOnlyPlusStrand ? '-' : (sjOptions.showOnlyMinusStrand ? '+' : undefined),
  labelUniqueReadCount: true,
  labelMultiMappedReadCount: false,
  labelTotalReadCount: false,
  labelMotif: false,
  labelAnnotatedJunction: false, //sjOptions.labelAnnotatedJunction && sjOptions.labelAnnotatedJunctionValue,
  hideAnnotatedJunctions: false,
  hideUnannotatedJunctions: false,
  //hideMotifs: SJ_MOTIFS.filter((motif) => sjOptions[`hideMotif${motif}`]), //options: 'GT/AG', 'CT/AC', 'GC/AG', 'CT/GC', 'AT/AC', 'GT/AT', 'non-canonical'
}

const TRACK_OPTIONS = {
  [ALIGNMENT_TYPE]: ALIGNMENT_TRACK_OPTIONS,
  [COVERAGE_TYPE]: COVERAGE_TRACK_OPTIONS,
  [JUNCTION_TYPE]: JUNCTION_TRACK_OPTIONS,
}

const getIgvOptions = (variant, igvSamples, individualsByGuid) => {
  // const igvTracksByIndividual = igvSamples.reduce((acc, sample) => {
  const igvTracksByIndividual = [
    ...igvSamples,
    { ...igvSamples[0], filePath: 'gs://macarthurlab-rnaseq/batch_0/junctions_bed_for_igv_js/250DV_LR_M1.junctions.bed.gz', sampleType: JUNCTION_TYPE },
    { ...igvSamples[0], filePath: 'gs://macarthurlab-rnaseq/batch_0/bigWig/250DV_LR_M1.bigWig', sampleType: COVERAGE_TYPE },
  ].reduce((acc, sample) => {
    const type = sample.sampleType || ALIGNMENT_TYPE // TODO

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
    }

    if (!acc[sample.individualGuid]) {
      acc[sample.individualGuid] = []
    }
    acc[sample.individualGuid].push({
      url,
      name: trackName,
      ...trackOptions,
    })
    return acc
  }, {})

  const igvTracks = Object.values(igvTracksByIndividual).reduce((acc, tracks) => ([
    ...acc,
    ...tracks.map((track) => {
      if (track.type === JUNCTION_TYPE) {
        const coverageTrack = tracks.find(({ type }) => (type === COVERAGE_TYPE))
        if (coverageTrack) {
          return {
            type: 'merged',
            name: track.name,
            height: track.height,
            tracks: [coverageTrack, track],
            // order: 12, TODO
          }
        }
      } else if (track.type === COVERAGE_TYPE && tracks.find(({ type }) => (type === JUNCTION_TYPE))) {
        return null
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

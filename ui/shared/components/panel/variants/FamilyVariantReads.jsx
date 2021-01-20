import React from 'react'
import ReactDOMServer from 'react-dom/server'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Segment, Icon } from 'semantic-ui-react'

import { updateIgvReadsVisibility } from 'redux/rootReducer'
import { getIndividualsByGuid, getIGVSamplesByFamily, getIgvReadsVisibility } from 'redux/selectors'
import PedigreeIcon from '../../icons/PedigreeIcon'
import IGV from '../../graph/IGV'
import { ButtonLink } from '../../StyledComponents'
import { VerticalSpacer } from '../../Spacers'
import { getLocus } from './Annotations'

const ALIGNMENT_TRACK_OPTIONS = {
  alignmentShading: 'strand',
  type: 'alignment',
  showSoftClips: true,
}

const CRAM_PROXY_TRACK_OPTIONS = {
  sourceType: 'pysam',
  alignmentFile: '/placeholder.cram',
  referenceFile: '/placeholder.fa',
  format: 'bam',
  ...ALIGNMENT_TRACK_OPTIONS,
}

const BAM_TRACK_OPTIONS = {
  indexed: true,
  format: 'bam',
  ...ALIGNMENT_TRACK_OPTIONS,
}

const COVERAGE_TRACK_OPTIONS = {
  type: 'wig',
  format: 'bigwig',
  height: 170,
  order: 11, // TODO
  rowName: 'row.name',
  categoryName: 'categoryName',
}

const JUNCTION_TRACK_OPTIONS = {
  type: 'spliceJunctions',
  format: 'bed',
  order: 10,
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
  rowName: 'row.name',
  categoryName: 'categoryName',
}

const FamilyVariantReads = React.memo(({ variant, igvSamples, individualsByGuid, hideReads }) => {

  if (!igvSamples || !igvSamples.length) {
    return null
  }

  // const igvTracks = igvSamples.map((sample) => {
  const igvTracks = [
    { ...igvSamples[0], filePath: 'gs://macarthurlab-rnaseq/batch_0/junctions_bed_for_igv_js/250DV_LR_M1.junctions.bed.gz' },
    // { ...igvSamples[0], filePath: 'gs://macarthurlab-rnaseq/batch_0/bigWig/250DV_LR_M1.bigWig' }
  ].map((sample) => {
    const individual = individualsByGuid[sample.individualGuid]

    const url = `/api/project/${sample.projectGuid}/igv_track/${encodeURIComponent(sample.filePath)}`

    let trackOptions = BAM_TRACK_OPTIONS
    if (sample.filePath.endsWith('.cram')) {
      if (sample.filePath.startsWith('gs://')) {
        trackOptions = {
          format: 'cram',
          indexURL: `${url}.crai`,
          ...ALIGNMENT_TRACK_OPTIONS,
        }
      } else {
        trackOptions = CRAM_PROXY_TRACK_OPTIONS
      }
    } else if (sample.filePath.endsWith('.bigWig')) {
      trackOptions = COVERAGE_TRACK_OPTIONS
    } else if (sample.filePath.endsWith('.junctions.bed.gz')) {
      trackOptions = {
        indexURL: `${url}.tbi`,
        ...JUNCTION_TRACK_OPTIONS,
      }
    }

    //
    // igvTracks.push({
    //   type: 'merged',
    //   name: junctionsTrack.name,
    //   height: sjOptions.trackHeight,
    //   tracks: [coverageTrack, junctionsTrack],
    //   order: 12,
    //   rowName: 'row.name',
    //   categoryName: 'categoryName',
    // })

    const trackName = ReactDOMServer.renderToString(
      <span><PedigreeIcon sex={individual.sex} affected={individual.affected} />{individual.displayName}</span>,
    )
    return {
      url,
      name: trackName,
      ...trackOptions,
    }
  }).filter(track => track)

  // TODO better determiner of genome version?
  const isBuild38 = igvSamples.some(sample => sample.filePath.endsWith('.cram'))
  const genome = isBuild38 ? 'hg38' : 'hg19'

  const locus = variant && getLocus(
    variant.chrom, (!isBuild38 && variant.liftedOverPos) ? variant.liftedOverPos : variant.pos, 100,
  )

  // igvTracks.push({
  //   url: `https://storage.googleapis.com/seqr-reference-data/${isBuild38 ? 'GRCh38' : 'GRCh37'}/gencode/gencode.v27${isBuild38 ? '' : 'lift37'}.annotation.sorted.gtf.gz`,
  //   name: `gencode ${genome}v27`,
  //   displayMode: 'SQUISHED',
  // })

  const igvOptions = {
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

  return (
    <Segment>
      <ButtonLink onClick={hideReads} icon={<Icon name="remove" color="grey" />} floated="right" size="large" />
      <VerticalSpacer height={20} />
      <IGV igvOptions={igvOptions} />
    </Segment>
  )
})

FamilyVariantReads.propTypes = {
  variant: PropTypes.object,
  igvSamples: PropTypes.array,
  individualsByGuid: PropTypes.object,
  hideReads: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => {
  const familyGuid = getIgvReadsVisibility(state)[ownProps.igvId || ownProps.variant.variantId]
  return {
    igvSamples: getIGVSamplesByFamily(state)[familyGuid],
    individualsByGuid: getIndividualsByGuid(state),
  }
}

const mapDispatchToProps = (dispatch, ownProps) => {
  return {
    hideReads: () => {
      dispatch(updateIgvReadsVisibility({ [ownProps.igvId || ownProps.variant.variantId]: null }))
    },
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(FamilyVariantReads)

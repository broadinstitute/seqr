import React from 'react'
import ReactDOMServer from 'react-dom/server'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Segment, Icon } from 'semantic-ui-react'

import { updateIgvReadsVisibility } from 'redux/rootReducer'
import { getIndividualsByGuid, getAlignmentSamplesByFamily, getIgvReadsVisibility } from 'redux/selectors'
import PedigreeIcon from '../../icons/PedigreeIcon'
import IGV from '../../graph/IGV'
import { ButtonLink } from '../../StyledComponents'
import { VerticalSpacer } from '../../Spacers'
import { getLocus } from './Annotations'

const CRAM_TRACK_OPTIONS = {
  sourceType: 'pysam',
  alignmentFile: '/placeholder.cram',
  referenceFile: '/placeholder.fa',
  showSoftClips: true,
}

const BAM_TRACK_OPTIONS = {
  indexed: true,
  showSoftClips: true,
}

const FamilyVariantReads = ({ variant, samples, individualsByGuid, hideReads }) => {

  if (!samples || !samples.length) {
    return null
  }

  const locus = variant && getLocus(variant.chrom, variant.pos, 100)

  const latestSamplesForIndividuals = samples.reduce((acc, sample) => {
    if (!acc[sample.individualGuid]) {
      acc[sample.individualGuid] = sample
    }
    return acc
  }, {})

  const igvTracks = Object.values(latestSamplesForIndividuals).map((sample) => {
    const individual = individualsByGuid[sample.individualGuid]

    const trackOptions = sample.datasetFilePath.endsWith('.cram') ? CRAM_TRACK_OPTIONS : BAM_TRACK_OPTIONS
    const trackName = ReactDOMServer.renderToString(
      <span><PedigreeIcon sex={individual.sex} affected={individual.affected} />{individual.displayName}</span>,
    )
    return {
      url: `/api/project/${sample.projectGuid}/igv_track/${encodeURIComponent(sample.datasetFilePath)}`,
      name: trackName,
      type: 'bam',
      alignmentShading: 'strand',
      ...trackOptions,
    }
  }).filter(track => track)

  // TODO better determiner of genome version?
  const isBuild38 = igvTracks.some(track => track.sourceType === 'pysam')
  const genome = isBuild38 ? 'hg38' : 'hg19'

  // TODO confirm cnv_bed_file track is deprecated (is empty for all existing individuals, so it should be)
  igvTracks.push({
    url: `https://storage.googleapis.com/seqr-reference-data/${isBuild38 ? 'GRCh38' : 'GRCh37'}/gencode/gencode.v27${isBuild38 ? '' : 'lift37'}.annotation.sorted.gtf.gz`,
    name: `gencode ${genome}v27`,
    displayMode: 'SQUISHED',
  })

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
}

FamilyVariantReads.propTypes = {
  variant: PropTypes.object,
  samples: PropTypes.array,
  individualsByGuid: PropTypes.object,
  hideReads: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => {
  const familyGuid = getIgvReadsVisibility(state)[ownProps.igvId || ownProps.variant.variantId]
  return {
    samples: getAlignmentSamplesByFamily(state)[familyGuid],
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

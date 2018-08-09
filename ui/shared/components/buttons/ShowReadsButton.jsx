import React from 'react'
import ReactDOMServer from 'react-dom/server'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Icon } from 'semantic-ui-react'

import { getIndividualsByGuid, getSamplesByGuid } from 'redux/selectors'
import Modal from '../modal/Modal'
import PedigreeIcon from '../icons/PedigreeIcon'
import IGV from '../graph/IGV'
import ButtonLink from './ButtonLink'
import { DATASET_TYPE_READ_ALIGNMENTS } from '../../utils/constants'
import { getLocus } from '../panel/variants/Annotations'

const CRAM_TRACK_OPTIONS = {
  sourceType: 'pysam',
  alignmentFile: '/placeholder.cram',
  referenceFile: '/placeholder.fa',
}

const BAM_TRACK_OPTIONS = {
  indexed: true,
}

const ShowReadsButton = ({ variant, familyGuid, samplesByGuid, individualsByGuid }) => {

  const locus = getLocus(variant, 100)

  const latestSamplesForIndividuals = Object.values(samplesByGuid).filter(sample => (
    sample.loadedDate &&
    sample.datasetType === DATASET_TYPE_READ_ALIGNMENTS &&
    individualsByGuid[sample.individualGuid].familyGuid === familyGuid
  )).reduce((acc, sample) => {
    if (!acc[sample.individualGuid] || acc[sample.individualGuid].loadedDate < sample.loadedDate) {
      acc[sample.individualGuid] = sample
    }
    return acc
  }, {})

  const igvTracks = Object.values(latestSamplesForIndividuals).map((sample) => {
    const individual = individualsByGuid[sample.individualGuid]

    const trackOptions = sample.datasetFilePath.endsWith('.cram') ? CRAM_TRACK_OPTIONS : BAM_TRACK_OPTIONS
    const trackName = ReactDOMServer.renderToString(
      <span><PedigreeIcon sex={individual.sex} affected={individual.affected} />{individual.individualId}</span>,
    )
    return {
      url: `/api/project/${sample.projectGuid}/igv_track/${encodeURIComponent(sample.datasetFilePath)}`,
      name: trackName,
      type: 'bam',
      alignmentShading: 'strand',
      ...trackOptions,
    }
  }).filter(track => track)

  if (igvTracks.length <= 0) {
    return null
  }

  // TODO better determiner of genome version?
  const genome = igvTracks.some(track => track.sourceType === 'pysam') ? 'GRCh38' : 'GRCh37'

  // TODO confirm cnv_bed_file track is deprecated (is empty for all existing individuals, so it should be)
  igvTracks.push({
    url: `https://storage.googleapis.com/seqr-reference-data/${genome}/gencode/gencode.v27${genome === 'GRCh37' ? 'lift37' : ''}.annotation.sorted.gtf.gz`,
    name: `gencode ${genome}v27`,
    displayMode: 'SQUISHED',
  })

  const igvOptions = {
    tracks: igvTracks,
    locus,
    genome,
    showIdeogram: true,
    showCenterGuide: true,
    showCursorTrackingGuide: true,
  }

  return (
    <Modal
      trigger={<ButtonLink><Icon name="options" /> SHOW READS</ButtonLink>}
      modalName={`${familyGuid}-${locus}-igv`}
      title="IGV"
      size="fullscreen"
    >
      <IGV igvOptions={igvOptions} />
    </Modal>
  )
}

ShowReadsButton.propTypes = {
  variant: PropTypes.object,
  familyGuid: PropTypes.string,
  samplesByGuid: PropTypes.object,
  individualsByGuid: PropTypes.object,
}

const mapStateToProps = state => ({
  samplesByGuid: getSamplesByGuid(state),
  individualsByGuid: getIndividualsByGuid(state),
})

export default connect(mapStateToProps)(ShowReadsButton)

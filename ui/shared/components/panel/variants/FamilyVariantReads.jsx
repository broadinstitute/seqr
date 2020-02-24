import React from 'react'
import ReactDOMServer from 'react-dom/server'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Segment, Icon } from 'semantic-ui-react'

import { updateIgvReadsVisibility } from 'redux/rootReducer'
import { getIndividualsByGuid, getActiveAlignmentSamplesByFamily, getIgvReadsVisibility } from 'redux/selectors'
import PedigreeIcon from '../../icons/PedigreeIcon'
import IGV from '../../graph/IGV'
import { ButtonLink } from '../../StyledComponents'
import { VerticalSpacer } from '../../Spacers'
import { getLocus } from './Annotations'

const CRAM_PROXY_TRACK_OPTIONS = {
  sourceType: 'pysam',
  alignmentFile: '/placeholder.cram',
  referenceFile: '/placeholder.fa',
  format: 'bam',
}

const BAM_TRACK_OPTIONS = {
  indexed: true,
  format: 'bam',
}

const FamilyVariantReads = React.memo(({ variant, activeSamples, individualsByGuid, hideReads }) => {

  if (!activeSamples || !activeSamples.length) {
    return null
  }

  const igvTracks = activeSamples.map((sample) => {
    const individual = individualsByGuid[sample.individualGuid]

    const url = `/api/project/${sample.projectGuid}/igv_track/${encodeURIComponent(sample.datasetFilePath)}`

    let trackOptions = BAM_TRACK_OPTIONS
    if (sample.datasetFilePath.endsWith('.cram')) {
      if (sample.datasetFilePath.startsWith('gs://')) {
        trackOptions = {
          format: 'cram',
          indexURL: `${url}.crai`,
        }
      } else {
        trackOptions = CRAM_PROXY_TRACK_OPTIONS
      }
    }

    const trackName = ReactDOMServer.renderToString(
      <span><PedigreeIcon sex={individual.sex} affected={individual.affected} />{individual.displayName}</span>,
    )
    return {
      url,
      name: trackName,
      alignmentShading: 'strand',
      type: 'alignment',
      showSoftClips: true,
      ...trackOptions,
    }
  }).filter(track => track)

  // TODO better determiner of genome version?
  const isBuild38 = activeSamples.some(sample => sample.datasetFilePath.endsWith('.cram'))
  const genome = isBuild38 ? 'hg38' : 'hg19'

  const locus = variant && getLocus(
    variant.chrom, (!isBuild38 && variant.liftedOverPos) ? variant.liftedOverPos : variant.pos, 100,
  )

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
})

FamilyVariantReads.propTypes = {
  variant: PropTypes.object,
  activeSamples: PropTypes.array,
  individualsByGuid: PropTypes.object,
  hideReads: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => {
  const familyGuid = getIgvReadsVisibility(state)[ownProps.igvId || ownProps.variant.variantId]
  return {
    activeSamples: getActiveAlignmentSamplesByFamily(state)[familyGuid],
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

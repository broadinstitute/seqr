import React from 'react'
import ReactDOMServer from 'react-dom/server'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Segment, Icon } from 'semantic-ui-react'

import { getIndividualsByGuid, getIGVSamplesByFamily } from 'redux/selectors'
import PedigreeIcon from '../icons/PedigreeIcon'
import IGV from '../graph/IGV'
import { ButtonLink } from '../StyledComponents'
import { VerticalSpacer } from '../Spacers'
import { getLocus } from './variants/Annotations'

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

const getIgvOptions = (variant, igvSamples, individualsByGuid) => {
  const igvTracks = igvSamples.map((sample) => {
    const individual = individualsByGuid[sample.individualGuid]

    const url = `/api/project/${sample.projectGuid}/igv_track/${encodeURIComponent(sample.filePath)}`

    let trackOptions = BAM_TRACK_OPTIONS
    if (sample.filePath.endsWith('.cram')) {
      if (sample.filePath.startsWith('gs://')) {
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
  igvTracks.map(console.log)

  return {
    locus,
    tracks: [], // TODO undo
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

class FamilyReads extends React.PureComponent {

  static propTypes = {
    variant: PropTypes.object,
    layout: PropTypes.any,
    familyGuid: PropTypes.string,
    buttonProps: PropTypes.object,
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
    const { variant, familyGuid, buttonProps, layout, igvSamplesByFamily, individualsByGuid, ...props } = this.props
    const familyGuids = variant ? variant.familyGuids : [familyGuid]

    const showReads = familyGuids.filter(fGuid => (igvSamplesByFamily[fGuid] || []).length > 0).map(fGuid =>
      //TODO better display for mutliple families
      <ButtonLink key={fGuid} icon="options" content="SHOW READS" onClick={this.showReads(fGuid)} {...buttonProps} />,
    )

    let reads = null
    const igvSamples = this.state.openFamily && igvSamplesByFamily[this.state.openFamily]
    if (igvSamples && igvSamples.length) {
      const igvOptions = getIgvOptions(variant, igvSamples, individualsByGuid)
      reads =
        <Segment>
          <ButtonLink onClick={this.hideReads} icon={<Icon name="remove" color="grey" />} floated="right" size="large" />
          <VerticalSpacer height={20} />
          <IGV igvOptions={igvOptions} />
        </Segment>
    }

    return React.createElement(layout, { variant, reads, showReads, ...props })
  }
}

const mapStateToProps = state => ({
  igvSamplesByFamily: getIGVSamplesByFamily(state),
  individualsByGuid: getIndividualsByGuid(state),
})

export default connect(mapStateToProps)(FamilyReads)

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import igv from 'igv/dist/igv.esm.min'

import { FontAwesomeIconsContainer } from '../StyledComponents'

const IGVContainer = styled(FontAwesomeIconsContainer)`
  .fa-lg {
    line-height: 1;
    vertical-align: middle;
    font-size: 1.5em;
  }
  
  .igv-zoom-widget i {
    line-height: 24px;
  }
`

const TRACK_UPDATE_PROPERTIES = ['minJunctionEndsVisible']

const getTrackId = track => track.url || track.name // merged tracks do not have a URL

class IGV extends React.PureComponent {

  static propTypes = {
    tracks: PropTypes.arrayOf(PropTypes.object),
    locus: PropTypes.string,
  }

  constructor(props) {
    super(props)
    this.container = null
    this.browser = null
  }

  componentDidMount() {
    if (this.container) {
      igv.createBrowser(this.container, { ...this.props }).then((browser) => {
        this.browser = browser
      })
    }
  }

  componentDidUpdate(prevProps) {
    const { tracks, locus } = this.props
    if (this.browser && locus !== prevProps.locus) {
      this.browser.search(locus)
    }
    if (this.browser && prevProps.tracks !== tracks) {
      const prevTracksById = prevProps.tracks.reduce((acc, track) => ({ ...acc, [getTrackId(track)]: track }), {})
      const prevTrackIds = Object.keys(prevTracksById)
      const newTrackIds = tracks.map(getTrackId)

      prevProps.tracks.filter(track => track.name && !newTrackIds.includes(getTrackId(track))).forEach((track) => {
        this.browser.removeTrackByName(track.name)
      })

      tracks.filter(track => !prevTrackIds.includes(getTrackId(track))).forEach((track) => {
        this.browser.loadTrack(track)
      })

      tracks.forEach((track) => {
        const prevTrack = track.name && prevTracksById[getTrackId(track)]
        if (prevTrack) {
          const optionChanged = (track.type === 'merged') ?
            track.tracks.some((tr, i) => TRACK_UPDATE_PROPERTIES.some(prop => tr[prop] !== prevTrack.tracks[i][prop])) :
            TRACK_UPDATE_PROPERTIES.some(prop => track[prop] !== prevTrack[prop])
          if (optionChanged) {
            this.browser.removeTrackByName(track.name)
            this.browser.loadTrack(track)
          }
        }
      })
    }
  }

  setContainerElement = (element) => {
    this.container = element
  }

  render() {
    return <IGVContainer><div ref={this.setContainerElement} /></IGVContainer>
  }

}

export default IGV

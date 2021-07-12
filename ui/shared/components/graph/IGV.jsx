import React from 'react'
import PropTypes from 'prop-types'
import igv from 'igv'

import { FontAwesomeIconsContainer } from '../StyledComponents'

const getTrackId = track =>
  // merged tracks do not have a URL
  track.url || track.name

class IGV extends React.PureComponent {

  static propTypes = {
    tracks: PropTypes.array,
  }

  constructor(props) {
    super(props)
    this.container = null
    this.browser = null
  }

  setContainerElement = (element) => {
    this.container = element
  }

  render() {
    return <FontAwesomeIconsContainer><div ref={this.setContainerElement} /></FontAwesomeIconsContainer>
  }

  componentDidMount() {
    if (this.container) {
      igv.createBrowser(this.container, { ...this.props }).then((browser) => {
        this.browser = browser
      })
    }
  }

  componentDidUpdate(prevProps) {
    if (this.browser && prevProps.tracks !== this.props.tracks) {
      const prevTrackIds = prevProps.tracks.map(getTrackId)
      const newTrackIds = this.props.tracks.map(getTrackId)

      prevProps.tracks.filter(track => track.name && !newTrackIds.includes(getTrackId(track))).forEach((track) => {
        this.browser.removeTrackByName(track.name)
      })

      this.props.tracks.filter(track => !prevTrackIds.includes(getTrackId(track))).forEach((track) => {
        this.browser.loadTrack(track)
      })

    }
  }
}

export default IGV

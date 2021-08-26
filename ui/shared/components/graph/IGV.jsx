import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import igv from 'igv'

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
    return <IGVContainer><div ref={this.setContainerElement} /></IGVContainer>
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

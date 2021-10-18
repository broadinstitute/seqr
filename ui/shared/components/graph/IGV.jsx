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

const getTrackId = track => track.url || track.name // merged tracks do not have a URL

class IGV extends React.PureComponent {

  static propTypes = {
    tracks: PropTypes.arrayOf(PropTypes.object),
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
    const { tracks } = this.props
    if (this.browser && prevProps.tracks !== tracks) {
      const prevTrackIds = prevProps.tracks.map(getTrackId)
      const newTrackIds = tracks.map(getTrackId)

      prevProps.tracks.filter(track => track.name && !newTrackIds.includes(getTrackId(track))).forEach((track) => {
        this.browser.removeTrackByName(track.name)
      })

      tracks.filter(track => !prevTrackIds.includes(getTrackId(track))).forEach((track) => {
        this.browser.loadTrack(track)
      })

      tracks.filter(track => prevTrackIds.includes(getTrackId(track))).forEach((track) => {
        if (track.name) {
          const prevTrack = prevProps.tracks.find(pTr => pTr.name === track.name)
          if (track.updated !== prevTrack.updated) {
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

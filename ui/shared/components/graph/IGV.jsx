import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import igv from 'igv'

// Map font-awesome icons to semantic-ui icons
const IGVContainer = styled.div`
  i.fa {
    display: inline-block;
    opacity: 1;
    margin: 0em 0.25rem 0em 0em;
    width: 1.18em;
    height: 1em;
    font-family: 'Icons';
    font-style: normal;
    font-weight: normal;
    text-decoration: inherit;
    text-align: center;
    speak: none;
    font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    -webkit-font-smoothing: antialiased;
    -webkit-backface-visibility: hidden;
    backface-visibility: hidden;
  }
  
  i.fa:before {
    background: none !important;
  }
  
  i.fa-fw {
    width: 1.2857142857142858em;
    text-align: center;
  }
  
  i.fa-lg {
    line-height: 1;
    vertical-align: middle;
    font-size: 1.5em;
  }
  
  i.fa-spin  {
    height: 1em;
    line-height: 1;
    -webkit-animation: icon-loading 2s linear infinite;
    animation: icon-loading 2s linear infinite;
  }
  
  i.fa-check:before {
    content: "\\f00c";
  }
  i.fa-square:before {
    content: "\\f098";
  } 
  i.fa-search:before {
    content: "\\f002";
  }
  i.fa-minus-circle:before {
    content: "\\f056";
  } 
  i.fa-plus-circle:before  {
    content: "\\f055";
  }
  i.fa-times:before  {
    content: "\\f00d";
  }  
  i.fa-times-circle:before  {
    content: "\\f057";
  } 
  i.fa-gear:before  {
    content: "\\f013";
  }
  i.fa-exclamation-triangle:before  {
    content: "\\f071";
  }  
  i.fa-spinner:before  {
    content: "\\f110";
  } 
  
  .igv-zoom-widget i {
    line-height: 24px;
  }
  
`

class IGV extends React.Component {

  static propTypes = {
    igvOptions: PropTypes.object.isRequired,
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
      igv.createBrowser(this.container, this.props.igvOptions).then((browser) => {
        this.browser = browser
      })
    }
  }

  componentDidUpdate(prevProps) {
    if (this.browser && prevProps.igvOptions.tracks !== this.props.igvOptions.tracks) {
      this.browser.removeAllTracks()
      this.props.igvOptions.tracks.forEach((track) => {
        this.browser.loadTrack(track)
      })

    }
  }
}

export default IGV

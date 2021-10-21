import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { SwatchesPicker } from 'react-color'
import { Popup } from 'semantic-ui-react'

const ColorSwatchBorder = styled.div`
  display: inline-block;
  cursor: pointer;
  border-radius: 2px;
  padding: 1px 2px;
  background: #fff;
  box-shadow: 0 0 0 1px rgba(0,0,0,.1);
`

const ColorSwatch = styled.div`
  display: inline-block;
  cursor: pointer;
  border-radius: 2px;
  box-shadow: 0 0 0 1px rgba(0,0,0,.1);
  width: 10px;
  height: 12px;
`

const StyledPopup = styled(Popup).attrs({ flowing: true })`
  padding: 0px !important;
  div {
    overflow-y: visible !important;
  }
`

class ColorPicker extends React.PureComponent {

  static propTypes = {
    color: PropTypes.string.isRequired,
    colorChangedHandler: PropTypes.func.isRequired,
  }

  state = { color: '' }

  componentDidMount() {
    const { color } = this.props
    this.setState({ color })
  }

  handleChange = (color) => {
    this.setState({ color })
  }

  handleApply = (color) => {
    const { colorChangedHandler } = this.props
    colorChangedHandler(color.hex)
  }

  render() {
    const { color } = this.state
    return (
      <StyledPopup
        on="click"
        position="left center"
        trigger={
          <ColorSwatchBorder>
            <ColorSwatch style={{ background: color }} />
          </ColorSwatchBorder>
        }
        content={
          <SwatchesPicker
            color={color}
            onChangeComplete={this.handleApply}
            onChange={newColor => this.setState({ color: newColor })}
          />
        }
      />
    )
  }

}

export default ColorPicker

import PropTypes from 'prop-types'
import styled from 'styled-components'

export const HorizontalSpacer = styled.div`
  display: inline-block;
  width: ${props => props.width}px;
`

HorizontalSpacer.propTypes = {
  width: PropTypes.number,
}

export const VerticalSpacer = styled.div`
  height: ${props => props.height}px;
`

VerticalSpacer.propTypes = {
  height: PropTypes.number,
}

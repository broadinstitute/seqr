import styled from 'styled-components'

export default styled.a.attrs({ role: 'button', tabIndex: '0' })`
  cursor: pointer;
  float: ${props => props.float || 'auto'}
`

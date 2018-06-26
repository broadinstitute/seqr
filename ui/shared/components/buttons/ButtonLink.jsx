import styled from 'styled-components'

export default styled.a.attrs({ role: 'button', tabIndex: '0' })`
  cursor: pointer;
  white-space: nowrap;
  float: ${props => props.float || 'inherit'};
  font-weight: ${props => props.fontWeight || 'inherit'};
  font-size: ${props => props.fontSize || 'inherit'};
`

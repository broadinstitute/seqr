import React from 'react'
import styled from 'styled-components'
import { Icon } from 'semantic-ui-react'

export default styled(({ color, ...props }) => <Icon {...props} />)`
  color: ${props => props.color};
`

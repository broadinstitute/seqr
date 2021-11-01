import React from 'react'
import randomMC from 'random-material-color'
import styled from 'styled-components'
import { Icon } from 'semantic-ui-react'

const getColor = categoryNames => (
  categoryNames.length === 0 ? '#ccc' : randomMC.getColor({ shades: ['300', '400', '500', '600', '700', '800'], text: categoryNames.sort().join(',') })
)

const ComputedColoredIcon = styled(({ categoryNames, ...props }) => <Icon {...props} />)`
  color: ${props => getColor(props.categoryNames)} !important;
`
export default ComputedColoredIcon

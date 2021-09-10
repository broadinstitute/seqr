import React from 'react'
import PropTypes from 'prop-types'
import { Grid } from 'semantic-ui-react'
import styled from 'styled-components'

const FamilyGrid = styled(({ annotation, offset, ...props }) => <Grid {...props} />)`
  margin-left: ${props => ((props.annotation || props.offset) ? '25px !important' : 'inherit')};
  margin-top: ${props => (props.annotation ? '-33px !important' : 'inherit')};
`

const getContentWidth = (useFullWidth, leftContent, rightContent) => {
  if (!useFullWidth || (leftContent && rightContent)) {
    return 10
  }
  if (leftContent || rightContent) {
    return 13
  }
  return 16
}

const FamilyLayout = React.memo(({ leftContent, rightContent, annotation, offset, fields, fieldDisplay, useFullWidth, compact }) =>
  <div>
    {annotation}
    <FamilyGrid annotation={annotation} offset={offset}>
      <Grid.Row>
        {(leftContent || !useFullWidth) && <Grid.Column width={3}>{leftContent}</Grid.Column>}
        {compact ? fields.map(field =>
          <Grid.Column width={field.colWidth || 1} key={field.id}>{fieldDisplay(field)}</Grid.Column>,
        ) : <Grid.Column width={getContentWidth(useFullWidth, leftContent, rightContent)}>{fields.map(field => fieldDisplay(field))}</Grid.Column>
        }
        {rightContent && <Grid.Column width={3}>{rightContent}</Grid.Column>}
      </Grid.Row>
    </FamilyGrid>
  </div>,
)

FamilyLayout.propTypes = {
  fieldDisplay: PropTypes.func,
  fields: PropTypes.array,
  useFullWidth: PropTypes.bool,
  compact: PropTypes.bool,
  offset: PropTypes.bool,
  annotation: PropTypes.node,
  leftContent: PropTypes.node,
  rightContent: PropTypes.node,
}

export default FamilyLayout

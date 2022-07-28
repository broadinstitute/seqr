import React from 'react'
import PropTypes from 'prop-types'
import { Table } from 'semantic-ui-react'
import styled from 'styled-components'

const FamilyGrid = styled(({ annotation, offset, ...props }) => <Table {...props} />)`
  margin-left: ${props => ((props.annotation || props.offset) ? '25px !important' : 'inherit')};
  margin-top: ${props => (props.annotation ? '-33px !important' : 'inherit')};
  background: inherit !important;
  border: none !important;
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

const FamilyLayout = React.memo((
  { leftContent, rightContent, annotation, offset, fields, fieldDisplay, useFullWidth, compact },
) => (
  <div>
    {annotation}
    <FamilyGrid annotation={annotation} offset={offset} compact fixed={!useFullWidth}>
      <Table.Body>
        <Table.Row verticalAlign="top">
          {(leftContent || !useFullWidth) && <Table.Cell width={3}>{leftContent}</Table.Cell>}
          {compact ? (fields || []).map(
            field => <Table.Cell width={field.colWidth || 1} key={field.id}>{fieldDisplay(field)}</Table.Cell>,
          ) : (
            <Table.Cell width={getContentWidth(useFullWidth, leftContent, rightContent)}>
              {(fields || []).map(field => fieldDisplay(field))}
            </Table.Cell>
          )}
          {rightContent && <Table.Cell width={3}>{rightContent}</Table.Cell>}
        </Table.Row>
      </Table.Body>
    </FamilyGrid>
  </div>
))

FamilyLayout.propTypes = {
  fieldDisplay: PropTypes.func,
  fields: PropTypes.arrayOf(PropTypes.object),
  useFullWidth: PropTypes.bool,
  compact: PropTypes.bool,
  offset: PropTypes.bool,
  annotation: PropTypes.node,
  leftContent: PropTypes.node,
  rightContent: PropTypes.node,
}

export default FamilyLayout

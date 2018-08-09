import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Link } from 'react-router-dom'
import { Popup, Table } from 'semantic-ui-react'

import { getVariantTagTypeCount } from 'shared/components/graph/VariantTagTypeBar'
import { ColoredIcon, HelpIcon } from 'shared/components/StyledComponents'

const TableRow = styled(Table.Row)`
  padding: 0px !important;`

const TableCell = styled(Table.Cell)`
  padding: 0 0 0 10px !important;`

const VariantTags = ({ project, familyGuids }) =>
  <Table basic="very" compact="very">
    <Table.Body>
      {
        project.variantTagTypes && project.variantTagTypes.map(variantTagType => (
          { count: getVariantTagTypeCount(variantTagType, familyGuids), ...variantTagType }
        )).filter(variantTagType => variantTagType.count > 0).map(variantTagType => (
          <TableRow key={variantTagType.variantTagTypeGuid}>
            <TableCell collapsing>
              <ColoredIcon name="square" size="small" color={variantTagType.color} />
              <b>{variantTagType.count} </b>
            </TableCell>
            <TableCell>
              <Link to={`/project/${project.projectGuid}/saved_variants/${variantTagType.name}`}>{variantTagType.name}</Link>
              {
                variantTagType.description &&
                <Popup
                  position="right center"
                  trigger={<HelpIcon />}
                  content={variantTagType.description}
                  size="small"
                />
              }
            </TableCell>
          </TableRow>),
        )
      }
    </Table.Body>
  </Table>


VariantTags.propTypes = {
  project: PropTypes.object.isRequired,
  familyGuids: PropTypes.array,
}

export default VariantTags

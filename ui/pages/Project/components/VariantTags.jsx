import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Link } from 'react-router-dom'
import { Popup, Icon, Table } from 'semantic-ui-react'

import { ColoredIcon } from 'shared/components/StyledComponents'

const HelpIcon = styled(Icon)`
  cursor: pointer;
  color: #555555; 
  margin-left: 15px;
`

const TableRow = styled(Table.Row)`
  padding: 0px !important;`

const TableCell = styled(Table.Cell)`
  padding: 0 0 0 10px !important;`

const VariantTags = ({ project }) =>
  <Table basic="very" compact="very">
    <Table.Body>
      {
        project.variantTagTypes && project.variantTagTypes.filter(variantTagType => variantTagType.numTags > 0).map(variantTagType => (
          <TableRow key={variantTagType.variantTagTypeGuid}>
            {
              // style={{ display: 'inline-block', minWidth: '35px', textAlign: 'right', fontSize: '11pt', paddingRight: '10px' }}>

            }
            <TableCell collapsing>
              <b>{variantTagType.numTags} </b>
              <ColoredIcon name="square" size="small" color={variantTagType.color} />
            </TableCell>
            <TableCell>
              <Link to={`/project/${project.projectGuid}/saved_variants/${variantTagType.name}`}>{variantTagType.name}</Link>
              {
                variantTagType.description &&
                <Popup
                  position="right center"
                  trigger={<HelpIcon name="help circle outline" />}
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
}

export default VariantTags

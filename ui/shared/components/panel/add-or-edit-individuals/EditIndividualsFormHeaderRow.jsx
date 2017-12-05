/* eslint-disable react/no-multi-comp */

import React from 'react'
import PropTypes from 'prop-types'
//import { Form, Table } from 'semantic-ui-react'
import styled from 'styled-components'


const TableHeaderRow = styled.tr`
  
`

const TableHeaderCell = styled.th`
  font-weight: 500;
  font-size: 1.12em;
  vertical-align: middle;
`

const FormCheckbox = styled.input`
  position: relative;
  top: 3px;
  padding-right: 15px;
`

class EditIndividualsFormRow extends React.Component
{
  static propTypes = {
    headerCheckboxHandler: PropTypes.func.isRequired,
  }

  shouldComponentUpdate() {
    return false
  }

  render() {
    return (
      <TableHeaderRow>
        <TableHeaderCell>
          <FormCheckbox type="checkbox" onClick={this.props.headerCheckboxHandler} />
          Family Id
        </TableHeaderCell>
        <TableHeaderCell style={{ paddingLeft: '32px' }}>
          Individual Id
        </TableHeaderCell>
        <TableHeaderCell style={{ paddingLeft: '50px' }}>
          Paternal Id
        </TableHeaderCell>
        <TableHeaderCell style={{ paddingLeft: '75px' }}>
          Maternal Id
        </TableHeaderCell>
        <TableHeaderCell style={{ paddingLeft: '100px' }}>
          Sex
        </TableHeaderCell>
        <TableHeaderCell style={{ paddingLeft: '55px' }}>
          Affected
        </TableHeaderCell>
      </TableHeaderRow>)
  }
}

export default EditIndividualsFormRow

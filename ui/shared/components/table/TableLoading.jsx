import React from 'react'
import { Table, Loader } from 'semantic-ui-react'

export default () =>
  <Table.Row>
    <Table.Cell colSpan="12"><Loader inline="centered" active /></Table.Cell>
  </Table.Row>

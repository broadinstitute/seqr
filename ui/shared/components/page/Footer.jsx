import React from 'react'
import styled from 'styled-components'
import { Table } from 'semantic-ui-react'

const TableHeaderCell = styled(Table.HeaderCell)`
  border-radius: 0 !important;
  font-weight: normal !important;
`

const Footer = () =>
  <Table>
    <Table.Header>
      <Table.Row>
        <TableHeaderCell width={2} />
        <TableHeaderCell width={7}>
          For bug reports or feature requests please submit  &nbsp;
          <a href="https://github.com/macarthur-lab/seqr/issues">Github Issues</a>
        </TableHeaderCell>
        <TableHeaderCell width={5} textAlign="right">
          If you have questions or feedback, &nbsp;
          <a
            href="https://mail.google.com/mail/?view=cm&amp;fs=1&amp;tf=1&amp;to=seqr@broadinstitute.org"
            target="_blank"
          >
            Contact Us
          </a>
        </TableHeaderCell>
        <TableHeaderCell width={2} />
      </Table.Row>
    </Table.Header>
  </Table>

export default Footer

import React from 'react'
import { Table, Form } from 'semantic-ui-react'

import TableBody from './table-body/TableBody'
import ExportTableLink from '../../../shared/components/ExportTableLink'
import { HorizontalSpacer, VerticalSpacer } from '../../../shared/components/Spacers'

const CaseReviewTable = () => <Form>
  <div className="nowrap" style={{ float: 'right' }}>
    <b>Download:</b> &nbsp;
    <ExportTableLink url="/">Family Table</ExportTableLink>, &nbsp;
    <ExportTableLink url="/">Individuals Table</ExportTableLink>
    <HorizontalSpacer width={63} /><br />
  </div><br />
  <VerticalSpacer height={3} />
  <Table celled style={{ width: '100%' }}>
    <TableBody />
  </Table>
</Form>

export default CaseReviewTable

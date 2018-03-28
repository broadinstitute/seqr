import React from 'react'
import { Grid, Table } from 'semantic-ui-react'


const TableFooterRow = () =>
  <Table.Row style={{ backgroundColor: '#F3F3F3' }} >
    <Table.Cell>
      <Grid stackable>
        <Grid.Column width={16} />
      </Grid>
    </Table.Cell>
  </Table.Row>


export { TableFooterRow as TableFooterRowComponent }

export default TableFooterRow

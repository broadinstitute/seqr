/* eslint-disable no-multi-spaces */

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'

import { Table, Icon, Popup } from 'semantic-ui-react'

const NameCell = styled(Table.Cell)`
 height: 20px;
 padding: 3px;
`

const LinkCell = styled(Table.Cell)`
  padding: 3px 3px 3px 20px;
  width: 80px;
 verticalAlign: middle;
`

const ExportTableButton = props =>
  <Popup
    trigger={
      <a href="#download">
        <Icon name="download" />Download Table
      </a>
    }
    content={
      <Table className="noBorder">
        <Table.Body className="noBorder">
          {
            props.urls.map(({ name, url }) => {
              if (!url.includes('?')) {
                url += '?'
              }
              if (!url.endsWith('?')) {
                url += '&'
              }
              return [
                <Table.Row key={1} className="noBorder">
                  <NameCell colSpan="2" className="noBorder">
                    <b>{name}:</b>
                  </NameCell>
                </Table.Row>,
                <Table.Row key={2} className="noBorder">
                  <LinkCell className="noBorder">
                    <a href={`${url}file_format=xls`}>
                      <img alt="xls" src="/static/images/table_excel.png" /> &nbsp; .xls
                    </a>
                  </LinkCell>
                  <LinkCell className="noBorder">
                    <a href={`${url}file_format=tsv`}>
                      <img alt="tsv" src="/static/images/table_tsv.png" /> &nbsp; .tsv
                    </a><br />
                  </LinkCell>
                </Table.Row>,
              ]
            })
          }
        </Table.Body>
      </Table>
    }
    on="click"
    position="bottom center"
  />


ExportTableButton.propTypes = {
  /**
   * An array of urls with names:
   *  [{ name: 'table1', url: '/table1-export'},  { name: 'table2', url: '/table2-export' }]
   */
  urls: PropTypes.array.isRequired,
}

export default ExportTableButton

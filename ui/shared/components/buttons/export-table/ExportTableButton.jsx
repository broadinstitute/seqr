/* eslint-disable no-multi-spaces */

import React from 'react'
import PropTypes from 'prop-types'

import { Icon, Popup } from 'semantic-ui-react'

const ExportTableButton = props =>
(
  <Popup
    trigger={
      <a href="#download">
        <Icon name="download" />Download Table
      </a>
    }
    content={
      <table>
        <tbody>
          {
            props.urls.map(({ name, url }) => {
              if (!url.includes('?')) {
                url += '?'
              }
              if (!url.endsWith('?')) {
                url += '&'
              }
              return [
                <tr>
                  <td colSpan="2" style={{ height: '20px', padding: '3px' }}><b>{name}:</b></td>
                </tr>,
                <tr>
                  <td style={{ padding: '3px 3px 3px 20px', width: '80px', verticalAlign: 'middle' }}>
                    <a href={`${url}file_format=xls`}>
                      <img alt="xls" src="/static/images/table_excel.png" /> &nbsp; .xls
                    </a>
                  </td>
                  <td style={{ padding: '3px 3px 3px 10px', width: '80px', verticalAlign: 'middle' }}>
                    <a href={`${url}file_format=tsv`}>
                      <img alt="tsv" src="/static/images/table_tsv.png" /> &nbsp; .tsv
                    </a><br />
                  </td>
                </tr>,
              ]
            })
          }
        </tbody>
      </table>
    }
    on="click"
    positioning="bottom center"
  />
)

ExportTableButton.propTypes = {
  /**
   * An array of urls with names:
   *  [{ name: 'table1', url: '/table1-export'},  { name: 'table2', url: '/table2-export' }]
   */
  urls: PropTypes.array.isRequired,
}

export default ExportTableButton

/* eslint-disable no-multi-spaces */

import React from 'react'
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
            props.urls.map(({ name, url }, i) => {
              return [
                <tr><td style={{ height: '20px', padding: '3px' }}><b>{name}:</b></td></tr>,
                <tr>
                  <td style={{ padding: '3px 3px 3px 20px', width: '100px', verticalAlign: 'middle' }}>
                    <a href={`${url}?format=xls`}><img alt="xls" src="/static/images/table_excel.png" /> &nbsp; .xls</a>
                  </td>
                </tr>,
                <tr>
                  <td style={{ padding: `3px 3px ${i < props.urls.length - 1 ? '15px' : '3px'} 20px` }}>
                    <a href={`${url}?format=tsv`}><img alt="tsv" src="/static/images/table_tsv.png" /> &nbsp; .tsv</a><br />
                  </td>
                </tr>,
              ]
            })
          }
        </tbody>
      </table>
    }
    on="click"
    position="bottom"
  />
)


ExportTableButton.propTypes = {
  urls: React.PropTypes.array.isRequired,
}

export default ExportTableButton

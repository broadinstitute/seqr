/* eslint-disable no-multi-spaces */
import React from 'react'
import { Popup } from 'semantic-ui-react'

const ExportTableButton = props =>
(
  <Popup
    trigger={<a href="#download">{props.children}</a>}
    content={<table>
      <tbody>
        <tr>
          <td height="20px">
            <b>Download Format:</b>
          </td>
        </tr>
        <tr><td width="100px"><a href={`${props.url}?format=xls`}>Excel (.xls)</a></td></tr>
        <tr><td><a href={`${props.url}?format=tsv`}>Tab-separated (.tsv)</a></td></tr>
      </tbody>
    </table>}
    on="click"
    position="bottom"
  />
)


ExportTableButton.propTypes = {
  children: React.PropTypes.node.isRequired,
  url: React.PropTypes.string.isRequired,
  //onClick: React.PropTypes.func.isRequired,
}

export default ExportTableButton

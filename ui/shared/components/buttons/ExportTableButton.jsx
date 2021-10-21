/* eslint-disable no-multi-spaces */

import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Table, Popup } from 'semantic-ui-react'

import { NoBorderTable, ButtonLink } from '../StyledComponents'

const NameCell = styled(Table.Cell)`
 height: 20px;
 padding: 3px;
`

const LinkCell = styled(Table.Cell)`
  padding: 3px 3px 3px 20px;
  width: 80px;
 verticalAlign: middle;
`

const EXT_CONFIG = {
  tsv: {
    dataType: 'tab-separated-values',
    delimiter: '\t',
  },
  xls: {
    imageName: 'excel',
    dataType: 'csv',
    delimiter: ',',
    dataExt: 'csv',
  },
}

const escapeExportItem = item => (item.replace ? item.replace(/"/g, '\'\'') : item)

export const BaseFileLink = React.memo(({ url, rawData, processRow, headers, filename, ext, linkContent }) => {
  const extConfig = EXT_CONFIG[ext]
  const linkBody = linkContent || (
    <span>
      <img alt={ext} src={`/static/images/table_${extConfig.imageName || ext}.png`} />
      {` .${ext}`}
    </span>
  )

  if (url) {
    const noQuery = !url.includes('?')
    const endQuery = noQuery || url.endsWith('?')
    return <a href={`${url}${noQuery ? '?' : ''}${!endQuery ? '&' : ''}file_format=${ext}`}>{linkBody}</a>
  }

  let content = rawData.map(row => processRow(row).map(
    item => `"${(item === null || item === undefined) ? '' : escapeExportItem(item)}"`,
  ).join(extConfig.delimiter)).join('\n')
  if (headers) {
    content = `${headers.join(extConfig.delimiter)}\n${content}`
  }
  const href = URL.createObjectURL(new Blob([content], {  type: 'application/octet-stream' }))

  return <a href={href} download={`${filename}.${extConfig.dataExt || ext}`}>{linkBody}</a>
})

BaseFileLink.propTypes = {
  ext: PropTypes.string.isRequired,
  url: PropTypes.string,
  rawData: PropTypes.arrayOf(PropTypes.object),
  processRow: PropTypes.func,
  headers: PropTypes.arrayOf(PropTypes.string),
  filename: PropTypes.string,
  linkContent: PropTypes.node,
}

const mapStateToProps = (state, ownProps) => ({
  rawData: ownProps.getRawData ? ownProps.getRawData(state, ownProps) : ownProps.rawData,
  headers: ownProps.getHeaders ? ownProps.getHeaders(state, ownProps) : ownProps.headers,
  filename: ownProps.getFilename ? ownProps.getFilename(state, ownProps) : ownProps.filename,
})

export const FileLink = connect(mapStateToProps)(BaseFileLink)

const ExportTableButton = React.memo(({ downloads, buttonText, downloadData, ...buttonProps }) => (
  <Popup
    trigger={
      <ButtonLink icon="download" content={buttonText || 'Download Table'} {...buttonProps} />
    }
    content={
      <NoBorderTable>
        <Table.Body>
          {
            downloads.map(({ name, ...downloadProps }) => ([
              <Table.Row key={1}>
                <NameCell colSpan="2">
                  <b>{`${name}:`}</b>
                </NameCell>
              </Table.Row>,
              <Table.Row key={2}>
                <LinkCell>
                  <FileLink {...downloadProps} downloadData={downloadData} ext="xls" />
                </LinkCell>
                <LinkCell>
                  <FileLink {...downloadProps} downloadData={downloadData} ext="tsv" />
                  <br />
                </LinkCell>
              </Table.Row>,
            ]))
          }
        </Table.Body>
      </NoBorderTable>
    }
    on="click"
    position="bottom center"
  />
))

ExportTableButton.propTypes = {
  /**
   * An array of urls with names:
   *  [{ name: 'table1', url: '/table1-export'},  { name: 'table2', url: '/table2-export' }]
   */
  downloads: PropTypes.arrayOf(PropTypes.object).isRequired,
  buttonText: PropTypes.string,
  downloadData: PropTypes.object,
}

export default ExportTableButton

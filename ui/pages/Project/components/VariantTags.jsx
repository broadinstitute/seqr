import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import styled from 'styled-components'
import { Link } from 'react-router-dom'
import { Popup, Table } from 'semantic-ui-react'

import { ColoredIcon, HelpIcon, NoBorderTable } from 'shared/components/StyledComponents'
import { NOTE_TAG_NAME } from 'shared/utils/constants'
import { getSavedVariantsLinkPath } from './VariantTagTypeBar'
import { getTagTypeData } from '../selectors'

const TableRow = styled(Table.Row)`
  padding: 0px !important;`

const TableCell = styled(Table.Cell)`
  padding: 0 0 0 10px !important;`

const getNoteTagType = (project) => {
  const noteType = (project.variantTagTypes || []).find(vtt => vtt.name === NOTE_TAG_NAME)
  return noteType && { ...noteType, count: noteType.numTags }
}

const VariantTags = React.memo(({ project, analysisGroupGuid, data }) => (
  <NoBorderTable basic="very" compact="very">
    <Table.Body>
      {
        [...data, analysisGroupGuid ? null : getNoteTagType(project)].filter(
          variantTagType => variantTagType && variantTagType.count > 0,
        ).map(variantTagType => (
          <TableRow key={variantTagType.variantTagTypeGuid}>
            <TableCell collapsing>
              <ColoredIcon name="square" size="small" color={variantTagType.color} />
              <b>{variantTagType.count}</b>
            </TableCell>
            <TableCell>
              <Link to={getSavedVariantsLinkPath({ project, analysisGroupGuid, tag: variantTagType.name })}>
                {variantTagType.name}
              </Link>
              {variantTagType.description && (
                <Popup
                  position="right center"
                  trigger={<HelpIcon />}
                  content={variantTagType.description}
                  size="small"
                />
              )}
            </TableCell>
          </TableRow>
        ))
      }
    </Table.Body>
  </NoBorderTable>
))

VariantTags.propTypes = {
  project: PropTypes.object.isRequired,
  data: PropTypes.arrayOf(PropTypes.object).isRequired,
  analysisGroupGuid: PropTypes.string,
}

const mapStateToProps = (state, ownProps) => ({
  data: getTagTypeData(state, ownProps),
})

export default connect(mapStateToProps)(VariantTags)

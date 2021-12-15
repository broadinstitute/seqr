import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import styled from 'styled-components'
import { Link } from 'react-router-dom'
import { Popup, Table } from 'semantic-ui-react'

import { ColoredIcon, HelpIcon, NoBorderTable } from 'shared/components/StyledComponents'
import { NOTE_TAG_NAME } from 'shared/utils/constants'
import { getSavedVariantsLinkPath } from './VariantTagTypeBar'
import { getProjectTagTypes } from '../selectors'

const TableRow = styled(Table.Row)`
  padding: 0px !important;`

const TableCell = styled(Table.Cell)`
  padding: 0 0 0 10px !important;`

const TagSummary = ({ variantTagType, count, project, analysisGroupGuid }) => (
  <TableRow>
    <TableCell collapsing>
      <ColoredIcon name="square" size="small" color={variantTagType.color} />
      <b>{count}</b>
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
)

TagSummary.propTypes = {
  variantTagType: PropTypes.object.isRequired,
  count: PropTypes.number,
  project: PropTypes.object,
  analysisGroupGuid: PropTypes.string,
}

const VariantTags = React.memo(({ project, analysisGroupGuid, tagTypes, tagTypeCounts }) => {
  const noteTagType = analysisGroupGuid ? null : (project.variantTagTypes || []).find(vtt => vtt.name === NOTE_TAG_NAME)
  return (
    <NoBorderTable basic="very" compact="very">
      <Table.Body>
        {
          tagTypes.filter(variantTagType => variantTagType && tagTypeCounts[variantTagType.name] > 0).map(
            variantTagType => (
              <TagSummary
                key={variantTagType.variantTagTypeGuid}
                variantTagType={variantTagType}
                count={tagTypeCounts[variantTagType.name]}
                project={project}
                analysisGroupGuid={analysisGroupGuid}
              />
            ),
          )
        }
        {noteTagType && noteTagType.numTags > 0 && (
          <TagSummary variantTagType={noteTagType} count={noteTagType.numTags} project={project} />
        )}
      </Table.Body>
    </NoBorderTable>
  )
})

VariantTags.propTypes = {
  project: PropTypes.object.isRequired,
  tagTypes: PropTypes.arrayOf(PropTypes.object).isRequired,
  tagTypeCounts: PropTypes.object,
  analysisGroupGuid: PropTypes.string,
}

const mapStateToProps = state => ({
  tagTypes: getProjectTagTypes(state),
})

export default connect(mapStateToProps)(VariantTags)

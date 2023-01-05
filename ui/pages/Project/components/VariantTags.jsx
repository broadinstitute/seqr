import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import styled from 'styled-components'
import { Link } from 'react-router-dom'
import { Popup, Table } from 'semantic-ui-react'

import { ColoredIcon, HelpIcon, NoBorderTable } from 'shared/components/StyledComponents'
import { NOTE_TAG_NAME } from 'shared/utils/constants'
import { VerticalSpacer } from 'shared/components/Spacers'
import VariantTagTypeBar, { getSavedVariantsLinkPath } from './VariantTagTypeBar'
import { getAnalysisGroupTagTypeCounts, getCurrentProject, getTagTypeCounts } from '../selectors'

const NOTE_TAGS = [NOTE_TAG_NAME]

const TableRow = styled(Table.Row)`
  padding: 0px !important;`

const TableCell = styled(Table.Cell)`
  padding: 0 0 0 10px !important;`

const TagSummary = ({ variantTagType, count, projectGuid, analysisGroupGuid }) => (
  <TableRow>
    <TableCell collapsing>
      <ColoredIcon name="square" size="small" color={variantTagType.color} />
      <b>{count}</b>
    </TableCell>
    <TableCell>
      <Link to={getSavedVariantsLinkPath({ projectGuid, analysisGroupGuid, tag: variantTagType.name })}>
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
  projectGuid: PropTypes.string,
  analysisGroupGuid: PropTypes.string,
}

const VariantTags = React.memo(({ project, analysisGroupGuid, tagTypes, tagTypeCounts }) => (
  <div>
    <VariantTagTypeBar
      projectGuid={project.projectGuid}
      analysisGroupGuid={analysisGroupGuid}
      tagTypes={tagTypes}
      tagTypeCounts={tagTypeCounts}
      height={20}
      excludeItems={NOTE_TAGS}
      showAllPopupCategories
    />
    <VerticalSpacer height={10} />
    <NoBorderTable basic="very" compact="very">
      <Table.Body>
        {
          tagTypes?.filter(variantTagType => variantTagType && tagTypeCounts[variantTagType.name] > 0).map(
            variantTagType => (
              <TagSummary
                key={variantTagType.variantTagTypeGuid}
                variantTagType={variantTagType}
                count={tagTypeCounts[variantTagType.name]}
                projectGuid={project.projectGuid}
                analysisGroupGuid={analysisGroupGuid}
              />
            ),
          )
        }
      </Table.Body>
    </NoBorderTable>
  </div>
))

VariantTags.propTypes = {
  project: PropTypes.object.isRequired,
  tagTypes: PropTypes.arrayOf(PropTypes.object).isRequired,
  tagTypeCounts: PropTypes.object,
  analysisGroupGuid: PropTypes.string,
}

const mapStateToProps = (state, ownProps) => ({
  project: getCurrentProject(state),
  tagTypes: getCurrentProject(state).variantTagTypes,
  tagTypeCounts: ownProps.analysisGroupGuid ?
    getAnalysisGroupTagTypeCounts(state, ownProps) : getTagTypeCounts(state),
})

export default connect(mapStateToProps)(VariantTags)

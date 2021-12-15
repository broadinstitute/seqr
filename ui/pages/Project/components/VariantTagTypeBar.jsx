import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'
import { EXCLUDED_TAG_NAME, REVIEW_TAG_NAME } from 'shared/utils/constants'
import { getProjectTagTypes } from '../selectors'

export const getSavedVariantsLinkPath = ({ project, analysisGroupGuid, familyGuid, tag }) => {
  let path = tag ? `/${tag}` : ''
  if (familyGuid) {
    path = `/family/${familyGuid}${path}`
  } else if (analysisGroupGuid) {
    path = `/analysis_group/${analysisGroupGuid}${path}`
  }

  return `/project/${project.projectGuid}/saved_variants${path}`
}

const VariantTagTypeBar = React.memo(({
  tagTypes, tagTypeCounts, project, familyGuid, analysisGroupGuid, sectionLinks = true, hideExcluded, hideReviewOnly,
  ...props
}) => (
  <HorizontalStackedBar
    {...props}
    minPercent={0.1}
    showPercent={false}
    showTotal={false}
    title="Saved Variants"
    noDataMessage="No Saved Variants"
    linkPath={getSavedVariantsLinkPath({ project, analysisGroupGuid, familyGuid })}
    sectionLinks={sectionLinks}
    dataCounts={tagTypeCounts}
    data={(hideExcluded || hideReviewOnly) ? tagTypes.filter(
      vtt => !(hideExcluded && vtt.name === EXCLUDED_TAG_NAME) && !(hideReviewOnly && vtt.name === REVIEW_TAG_NAME),
    ) : tagTypes}
  />
))

VariantTagTypeBar.propTypes = {
  project: PropTypes.object.isRequired,
  tagTypes: PropTypes.arrayOf(PropTypes.object).isRequired,
  tagTypeCounts: PropTypes.object,
  familyGuid: PropTypes.string,
  analysisGroupGuid: PropTypes.string,
  sectionLinks: PropTypes.bool,
  hideExcluded: PropTypes.bool,
  hideReviewOnly: PropTypes.bool,
}

const mapStateToProps = state => ({
  tagTypes: getProjectTagTypes(state),
})

export default connect(mapStateToProps)(VariantTagTypeBar)

import React from 'react'
import PropTypes from 'prop-types'

import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'

export const getSavedVariantsLinkPath = ({ projectGuid, analysisGroupGuid, familyGuid, tag }) => {
  let path = tag ? `/${tag}` : ''
  if (familyGuid) {
    path = `/family/${familyGuid}${path}`
  } else if (analysisGroupGuid) {
    path = `/analysis_group/${analysisGroupGuid}${path}`
  }

  return `/project/${projectGuid}/saved_variants${path}`
}

const VariantTagTypeBar = React.memo(({
  tagTypes, tagTypeCounts, projectGuid, familyGuid, analysisGroupGuid, sectionLinks = true, ...props
}) => (
  <HorizontalStackedBar
    {...props}
    minPercent={0.1}
    showPercent={false}
    showTotal={false}
    title="Saved Variants"
    noDataMessage="No Saved Variants"
    linkPath={getSavedVariantsLinkPath({ projectGuid, analysisGroupGuid, familyGuid })}
    sectionLinks={sectionLinks}
    dataCounts={tagTypeCounts}
    data={tagTypes}
  />
))

VariantTagTypeBar.propTypes = {
  projectGuid: PropTypes.string.isRequired,
  tagTypes: PropTypes.arrayOf(PropTypes.object),
  tagTypeCounts: PropTypes.object,
  familyGuid: PropTypes.string,
  analysisGroupGuid: PropTypes.string,
  sectionLinks: PropTypes.bool,
  hideExcluded: PropTypes.bool,
  hideReviewOnly: PropTypes.bool,
}

export default VariantTagTypeBar

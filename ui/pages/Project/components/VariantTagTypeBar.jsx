import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import HorizontalStackedBar from 'shared/components/graph/HorizontalStackedBar'
import { EXCLUDED_TAG_NAME, REVIEW_TAG_NAME } from 'shared/utils/constants'
import { getTagTypeData, getTagTypeDataByFamily } from '../selectors'

export const getSavedVariantsLinkPath = ({ project, analysisGroup, familyGuid, tag }) => {
  let path = tag ? `/${tag}` : ''
  if (familyGuid) {
    path = `/family/${familyGuid}${path}`
  } else if (analysisGroup) {
    path = `/analysis_group/${analysisGroup.analysisGroupGuid}${path}`
  }

  return `/project/${project.projectGuid}/saved_variants${path}`
}

const VariantTagTypeBar = React.memo((
  { data, project, familyGuid, analysisGroup, sectionLinks = true, hideExcluded, hideReviewOnly, ...props },
) => (
  <HorizontalStackedBar
    {...props}
    minPercent={0.1}
    showPercent={false}
    showTotal={false}
    title="Saved Variants"
    noDataMessage="No Saved Variants"
    linkPath={getSavedVariantsLinkPath({ project, analysisGroup, familyGuid })}
    sectionLinks={sectionLinks}
    data={(hideExcluded || hideReviewOnly) ? data.filter(
      vtt => !(hideExcluded && vtt.name === EXCLUDED_TAG_NAME) && !(hideReviewOnly && vtt.name === REVIEW_TAG_NAME),
    ) : data}
  />
))

VariantTagTypeBar.propTypes = {
  project: PropTypes.object.isRequired,
  data: PropTypes.arrayOf(PropTypes.object).isRequired,
  familyGuid: PropTypes.string,
  analysisGroup: PropTypes.object, // TODO clean up, can probably just ge the guid
  sectionLinks: PropTypes.bool,
  hideExcluded: PropTypes.bool,
  hideReviewOnly: PropTypes.bool,
}

const mapStateToProps = (state, ownProps) => ({
  data: ownProps.familyGuid ?
    getTagTypeDataByFamily(state)[ownProps.familyGuid] || [] : getTagTypeData(state, ownProps),
})

export default connect(mapStateToProps)(VariantTagTypeBar)

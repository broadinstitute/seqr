import React from 'react'
import PropTypes from 'prop-types'

import HorizontalStackedBar from '../graph/HorizontalStackedBar'
import { EXCLUDED_TAG_NAME, REVIEW_TAG_NAME, NOTE_TAG_NAME } from '../../utils/constants'

export const getVariantTagTypeCount = (vtt, familyGuids) => (
  familyGuids ? familyGuids.reduce((count, familyGuid) => count + (vtt.numTagsPerFamily[familyGuid] || 0), 0) : vtt.numTags
)

export const getSavedVariantsLinkPath = ({ project, analysisGroup, familyGuid, tag }) => {
  let path = tag ? `/${tag}` : ''
  if (familyGuid) {
    path = `/family/${familyGuid}${path}`
  } else if (analysisGroup) {
    path = `/analysis_group/${analysisGroup.analysisGroupGuid}${path}`
  }
  const urlRoot = project ? `/project/${project.projectGuid}` : '/staff'
  return `${urlRoot}/saved_variants${path}`
}

const VariantTagTypeBar = ({ project, familyGuid, analysisGroup, sectionLinks = true, hideExcluded, hideReviewOnly, ...props }) => (
  <HorizontalStackedBar
    {...props}
    minPercent={0.1}
    showPercent={false}
    showTotal={false}
    title="Saved Variants"
    noDataMessage="No Saved Variants"
    linkPath={getSavedVariantsLinkPath({ project, analysisGroup, familyGuid })}
    sectionLinks={sectionLinks}
    data={(project.variantTagTypes || []).filter(
      vtt => vtt.name !== NOTE_TAG_NAME && !(hideExcluded && vtt.name === EXCLUDED_TAG_NAME) && !(hideReviewOnly && vtt.name === REVIEW_TAG_NAME),
    ).map((vtt) => {
      return { count: getVariantTagTypeCount(vtt,
          familyGuid ? [familyGuid] : (analysisGroup || {}).familyGuids),
        ...vtt }
    })}
  />
)

VariantTagTypeBar.propTypes = {
  project: PropTypes.object.isRequired,
  familyGuid: PropTypes.string,
  analysisGroup: PropTypes.object,
  sectionLinks: PropTypes.bool,
  hideExcluded: PropTypes.bool,
  hideReviewOnly: PropTypes.bool,
}

export default VariantTagTypeBar

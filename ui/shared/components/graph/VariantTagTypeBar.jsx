import React from 'react'
import PropTypes from 'prop-types'

import HorizontalStackedBar from '../graph/HorizontalStackedBar'
import { EXCLUDED_TAG_NAME, REVIEW_TAG_NAME } from '../../utils/constants'


export const getVariantTagTypeCount = (vtt, familyGuids) => (
  familyGuids ? familyGuids.reduce((count, familyGuid) => count + (vtt.numTagsPerFamily[familyGuid] || 0), 0) : vtt.numTags
)

const VariantTagTypeBar = ({ project, familyGuid, familyGuids, sectionLinks = true, hideExcluded, hideReviewOnly, ...props }) =>
  <HorizontalStackedBar
    {...props}
    minPercent={0.1}
    showPercent={false}
    showTotal={false}
    title="Saved Variants"
    noDataMessage="No Saved Variants"
    linkPath={`/project/${project.projectGuid}/saved_variants${familyGuid ? `/family/${familyGuid}` : ''}`}
    sectionLinks={sectionLinks}
    data={(project.variantTagTypes || []).filter(
      vtt => !(hideExcluded && vtt.name === EXCLUDED_TAG_NAME) && !(hideReviewOnly && vtt.name === REVIEW_TAG_NAME),
    ).map((vtt) => {
      return { count: getVariantTagTypeCount(vtt, familyGuid ? [familyGuid] : familyGuids), ...vtt }
    })}
  />

VariantTagTypeBar.propTypes = {
  project: PropTypes.object.isRequired,
  familyGuid: PropTypes.string,
  familyGuids: PropTypes.array,
  sectionLinks: PropTypes.bool,
  hideExcluded: PropTypes.bool,
  hideReviewOnly: PropTypes.bool,
}

export default VariantTagTypeBar

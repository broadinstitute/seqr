import React from 'react'
import PropTypes from 'prop-types'

import HorizontalStackedBar from '../graph/HorizontalStackedBar'


const VariantTagTypeBar = ({ project, familyGuid, ...props }) =>
  <HorizontalStackedBar
    {...props}
    minPercent={0.1}
    showPercent={false}
    title={`Saved ${familyGuid ? 'Family ' : ''}Variants`}
    noDataMessage="No Saved Variants"
    linkPath={`/project/${project.projectGuid}/saved_variants${familyGuid ? `/family/${familyGuid}` : ''}`}
    data={(project.variantTagTypes || []).map((vtt) => {
      return { count: familyGuid ? vtt.tagCounts[familyGuid] || 0 : vtt.numTags, ...vtt }
    })}
  />

VariantTagTypeBar.propTypes = {
  project: PropTypes.object.isRequired,
  familyGuid: PropTypes.string,
}

export default VariantTagTypeBar

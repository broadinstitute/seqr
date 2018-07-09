import React from 'react'
import PropTypes from 'prop-types'

import HorizontalStackedBar from '../graph/HorizontalStackedBar'


const VariantTagTypeBar = ({ project, familyGuid, sectionLinks = true, ...props }) =>
  <HorizontalStackedBar
    {...props}
    minPercent={0.1}
    showPercent={false}
    showTotal={false}
    title={`Saved ${familyGuid ? 'Family ' : ''}Variants`}
    noDataMessage="No Saved Variants"
    linkPath={`/project/${project.projectGuid}/saved_variants${familyGuid ? `/family/${familyGuid}` : ''}`}
    sectionLinks={sectionLinks}
    data={(project.variantTagTypes || []).map((vtt) => {
      return { count: familyGuid ? vtt.numTagsPerFamily[familyGuid] || 0 : vtt.numTags, ...vtt }
    })}
  />

VariantTagTypeBar.propTypes = {
  project: PropTypes.object.isRequired,
  familyGuid: PropTypes.string,
  sectionLinks: PropTypes.bool,
}

export default VariantTagTypeBar

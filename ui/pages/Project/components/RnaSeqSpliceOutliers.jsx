import React from 'react'
import PropTypes from 'prop-types'

import { GeneSearchLink } from 'shared/components/buttons/SearchResultsLink'
import RnaSeqOutlierVolcanoPlot from './RnaSeqOutlierVolcanoPlot'

const RnaSeqSpliceOutliers = React.memo((
  { rnaSeqData, genesById, familyGuid },
) => (
  <div>
    <GeneSearchLink
      buttonText="Search for variants in outlier genes"
      icon="search"
      location={Object.values(rnaSeqData || {}).filter(({ isSignificant }) => isSignificant).map(({ geneId }) => geneId).join(',')}
      familyGuid={familyGuid}
      floated="right"
    />
    <RnaSeqOutlierVolcanoPlot data={rnaSeqData} genesById={genesById} />
  </div>
))

RnaSeqSpliceOutliers.propTypes = {
  familyGuid: PropTypes.string.isRequired,
  rnaSeqData: PropTypes.object,
  genesById: PropTypes.object,
}

export default RnaSeqSpliceOutliers

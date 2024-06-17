import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Popup, Icon } from 'semantic-ui-react'

import { HorizontalSpacer, VerticalSpacer } from '../Spacers'
import { DATASET_TYPE_SNV_INDEL_CALLS, SAMPLE_TYPE_RNA } from '../../utils/constants'

const Detail = styled.span`
  font-size: 11px;
  color: #999999;
`

const iconColor = (loadedSample, isOutdated) => {
  if (!loadedSample) return 'red'
  return isOutdated ? 'grey' : 'green'
}

const Sample = React.memo(({ loadedSample, isOutdated, hoverDetails }) => (
  <Popup
    trigger={
      <span>
        <Icon size="small" name="circle" color={iconColor(loadedSample, isOutdated)} />
        {loadedSample && <b>{loadedSample.sampleType}</b>}
        {loadedSample && loadedSample.datasetType && loadedSample.datasetType !== DATASET_TYPE_SNV_INDEL_CALLS && ` - ${loadedSample.datasetType}`}
        {
          !hoverDetails && (loadedSample ? (
            <Detail>
              <HorizontalSpacer width={6} />
              {`LOADED ${new Date(loadedSample.loadedDate).toLocaleDateString().toUpperCase()}`}
            </Detail>
          ) : <small>NO LOADED DATA</small>)
        }
      </span>
    }
    content={
      <div>
        {loadedSample ?
          `data was${isOutdated ? ' previously ' : ''} ${hoverDetails ? `${hoverDetails} on ${new Date(loadedSample.loadedDate).toLocaleDateString()}` : 'loaded'}` :
          'no data available'}
        <VerticalSpacer height={5} />
        {loadedSample.sampleType && loadedSample.sampleType === SAMPLE_TYPE_RNA &&
          loadedSample.rnaSeqTypes?.length > 0 && `RNAseq methods: ${loadedSample.rnaSeqTypes.join(', ')}`}
      </div>
    }
    position="left center"
  />
))

Sample.propTypes = {
  loadedSample: PropTypes.object,
  isOutdated: PropTypes.bool,
  hoverDetails: PropTypes.string,
}

export default Sample

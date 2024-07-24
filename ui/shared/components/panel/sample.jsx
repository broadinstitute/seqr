import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Popup, Icon } from 'semantic-ui-react'

import { HorizontalSpacer } from '../Spacers'
import { DATASET_TYPE_SNV_INDEL_CALLS } from '../../utils/constants'

const Detail = styled.span`
  font-size: 11px;
  color: #999999;
`

const iconColor = (loadedSample, isOutdated) => {
  if (!loadedSample) return 'red'
  return isOutdated ? 'grey' : 'green'
}

const Sample = React.memo(({ sampleType, datasetType, loadedDate, hoverContent, isOutdated, hoverDetails }) => (
  <Popup
    trigger={
      <span>
        <Icon size="small" name="circle" color={iconColor(sampleType, isOutdated)} />
        {sampleType && <b>{sampleType}</b>}
        {datasetType && datasetType !== DATASET_TYPE_SNV_INDEL_CALLS && ` - ${datasetType}`}
        {
          !hoverDetails && (loadedDate ? (
            <Detail>
              <HorizontalSpacer width={6} />
              {`LOADED ${new Date(loadedDate).toLocaleDateString().toUpperCase()}`}
            </Detail>
          ) : <small>NO LOADED DATA</small>)
        }
      </span>
    }
    content={
      <div>
        {!hoverContent && (loadedDate ?
          `data was${isOutdated ? ' previously ' : ''} ${hoverDetails ? `${hoverDetails} on ${new Date(loadedDate).toLocaleDateString()}` : 'loaded'}` :
          'no data available')}
        {hoverContent}
      </div>
    }
    position="left center"
  />
))

Sample.propTypes = {
  sampleType: PropTypes.string,
  datasetType: PropTypes.string,
  loadedDate: PropTypes.string,
  hoverContent: PropTypes.string,
  isOutdated: PropTypes.bool,
  hoverDetails: PropTypes.string,
}

export default Sample

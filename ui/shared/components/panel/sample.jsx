import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Popup, Icon } from 'semantic-ui-react'

import { HorizontalSpacer } from '../Spacers'

const Detail = styled.span`
  font-size: 11px;
  color: #999999;
`

const iconColor = (loadedSample, isOutdated) => {
  if (!loadedSample) return 'red'
  return isOutdated ? 'grey' : 'green'
}

const Sample = ({ loadedSample, isOutdated, hoverDetails }) =>
  <Popup
    trigger={
      <span>
        <Icon size="small" name="circle" color={iconColor(loadedSample, isOutdated)} />
        {loadedSample && <b>{loadedSample.sampleType}</b>}
        {
          !hoverDetails && (loadedSample ?
            <Detail>
              <HorizontalSpacer width={6} />
              LOADED {new Date(loadedSample.loadedDate).toLocaleDateString().toUpperCase()}
            </Detail> : <small>NO LOADED DATA</small>)
        }
      </span>
    }
    content={loadedSample ?
      `data was${isOutdated ? ' previously ' : ''} ${hoverDetails ? `${hoverDetails} on ${new Date(loadedSample.loadedDate).toLocaleDateString()}` : 'loaded'}` :
      'no data available'
    }
    position="left center"
  />

Sample.propTypes = {
  loadedSample: PropTypes.object,
  isOutdated: PropTypes.bool,
  hoverDetails: PropTypes.string,
}

export default Sample

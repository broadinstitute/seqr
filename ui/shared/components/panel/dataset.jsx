import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Popup, Icon } from 'semantic-ui-react'

import { HorizontalSpacer } from '../Spacers'

const Detail = styled.span`
  font-size: 11px;
  color: #999999;
`

const iconColor = (loadedDataset, isOutdated) => {
  if (!loadedDataset) return 'red'
  return isOutdated ? 'yellow' : 'green'
}

const Dataset = ({ loadedDataset, isOutdated }) =>
  <span>
    <Popup
      trigger={<Icon size="small" name="circle" color={iconColor(loadedDataset, isOutdated)} />}
      content={loadedDataset ? `data has been ${isOutdated ? 're-' : ''}loaded` : 'no data available'}
      position="left center"
    />
    <HorizontalSpacer width={8} />
    {loadedDataset ? <b>{loadedDataset.sampleType}</b> : <small>NO LOADED DATA</small>}
    {
      loadedDataset &&
      <Detail>
        <HorizontalSpacer width={6} />
        LOADED {new Date(loadedDataset.loadedDate).toLocaleDateString().toUpperCase()}
      </Detail>
    }
  </span>

Dataset.propTypes = {
  loadedDataset: PropTypes.object,
  isOutdated: PropTypes.bool,
}

export default Dataset

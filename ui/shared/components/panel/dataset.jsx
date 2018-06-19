import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { Popup, Icon } from 'semantic-ui-react'

import { HorizontalSpacer } from '../Spacers'

const Detail = styled.span`
  font-size: 11px;
  color: #999999;
`

const Dataset = ({ loadedDataset }) =>
  <span>
    <Popup
      trigger={<Icon size="small" name="circle" color={loadedDataset ? 'green' : 'red'} />}
      content={loadedDataset ? 'data has been loaded' : 'no data available'}
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
}

export default Dataset

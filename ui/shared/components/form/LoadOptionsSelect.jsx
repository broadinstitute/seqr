import React from 'react'
import PropTypes from 'prop-types'

import { Select } from 'shared/components/form/Inputs'
import StateDataLoader from '../StateDataLoader'

const parseResponse = optionsResponseKey => responseJson => (
  { options: responseJson[optionsResponseKey]?.map(value => ({ name: value, value })) }
)

const validateResponse = ({ options }) => (!!options && options.length > 0)

const LoadOptionsSelect = ({ optionsResponseKey, ...props }) => (
  <StateDataLoader
    childComponent={Select}
    parseResponse={parseResponse(optionsResponseKey)}
    validateResponse={validateResponse}
    {...props}
  />
)

LoadOptionsSelect.propTypes = {
  url: PropTypes.string.isRequired,
  optionsResponseKey: PropTypes.string.isRequired,
  errorHeader: PropTypes.string,
  validationErrorHeader: PropTypes.string,
  validationErrorMessage: PropTypes.string,
}

export default LoadOptionsSelect

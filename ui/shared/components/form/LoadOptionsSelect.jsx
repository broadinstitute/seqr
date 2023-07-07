import React from 'react'
import PropTypes from 'prop-types'

import { Select } from 'shared/components/form/Inputs'
import StateDataLoader from '../StateDataLoader'

const defaultFormatOption = value => ({ name: value, value })

const parseResponse = (optionsResponseKey, formatOption) => responseJson => (
  { options: responseJson[optionsResponseKey]?.map(formatOption || defaultFormatOption) }
)

const validateResponse = ({ options }) => (!!options && options.length > 0)

const LoadOptionsSelect = ({ optionsResponseKey, formatOption, ...props }) => (
  <StateDataLoader
    childComponent={Select}
    parseResponse={parseResponse(optionsResponseKey, formatOption)}
    validateResponse={validateResponse}
    {...props}
  />
)

LoadOptionsSelect.propTypes = {
  url: PropTypes.string.isRequired,
  optionsResponseKey: PropTypes.string.isRequired,
  formatOption: PropTypes.func,
  errorHeader: PropTypes.string,
  validationErrorHeader: PropTypes.string,
  validationErrorMessage: PropTypes.string,
}

export default LoadOptionsSelect

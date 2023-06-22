import React from 'react'
import PropTypes from 'prop-types'
import { Segment } from 'semantic-ui-react'

import StateDataLoader from 'shared/components/StateDataLoader'

const LOAD_PROJECT_OPTION_URL = '/api/data_management/loadable_project_options'

const LoadData = ({ projectOptions }) => <Segment>{JSON.stringify(projectOptions)}</Segment>

LoadData.propTypes = {
  projectOptions: PropTypes.object,
}

const validateResponse = ({ projectOptions }) => projectOptions && projectOptions.length

export default () => (
  <StateDataLoader
    url={LOAD_PROJECT_OPTION_URL}
    childComponent={LoadData}
    validateResponse={validateResponse}
    validationErrorMessage="No Projects Available for Data Loading"
  />
)

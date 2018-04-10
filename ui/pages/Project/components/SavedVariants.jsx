import React from 'react'
import PropTypes from 'prop-types'

const SavedVariants = ({ match }) =>
  <div>
    Saved Variant Page: {JSON.stringify(match)}
  </div>

SavedVariants.propTypes = {
  match: PropTypes.object,
}

export default SavedVariants

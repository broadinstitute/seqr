import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { ButtonLink } from 'shared/components/StyledComponents'
import MessagesPanel from 'shared/components/form/MessagesPanel'
import DataLoader from 'shared/components/DataLoader'
import { getGoogleAuthIsLoading, getGoogleAuthIsLoadingError } from 'redux/selectors'
import { loadGoogleAuthResult } from '../reducers'

const GoogleAuth = React.memo(({ location, load, loading, errorMessage }) => {
  const errMsgs = [errorMessage]
  return (
    <div>
      <DataLoader contentId={location} content={location} load={load} loading={loading}>
        <MessagesPanel errors={errMsgs} />
      </DataLoader>
      {errorMessage ?
        <ButtonLink
          content="Close"
          labelPosition="right"
          size="small"
          onClick={() => { window.close(); window.opener.focus() }}
        /> : null }
    </div>) },
)

GoogleAuth.propTypes = {
  location: PropTypes.object.isRequired,
  load: PropTypes.func.isRequired,
  loading: PropTypes.bool.isRequired,
  errorMessage: PropTypes.string,
}

const mapDispatchToProps = {
  load: loadGoogleAuthResult,
}

const mapStateToProps = state => ({
  loading: getGoogleAuthIsLoading(state),
  errorMessage: getGoogleAuthIsLoadingError(state),
})

export default connect(mapStateToProps, mapDispatchToProps)(GoogleAuth)

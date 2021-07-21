import React from 'react'
import PropTypes from 'prop-types'
import { Segment, Message, Button, Icon } from 'semantic-ui-react'

import { ANVIL_URL, GOOGLE_LOGIN_URL } from 'shared/utils/constants'

const GOGGLE_SETUP_URL = 'https://support.terra.bio/hc/en-us/articles/360029186611-Setting-up-a-Google-account-with-a-non-Google-email'

const ERROR_MESSAGES = {
  anvil_registration: (
    <span>
      Unable to authorize the selected Google user.
      Please register your account in AnVIL by signing in and registering
      at <a href={ANVIL_URL} target="_blank">anvil.terra.bio</a>. <br />
      If you have already registered your account, please log in to AnVIL and confirm
      you have accepted their latest terms of service.  <br />
      If the email associated with your account is not managed by google,
      follow <a href={GOGGLE_SETUP_URL} target="_blank">these instructions </a>
      to register the email with google before registering with AnVIL.
    </span>
  ),
  no_account: 'No seqr account found for the selected Google user',
}

const LoginError = ({ location, match }) => (
  <Segment textAlign="center" padded="very" basic>
    <Message error compact>
      {ERROR_MESSAGES[match.params.error] || `Unknown error occured: ${match.params.error}`}
    </Message>
    <div>
      <Button as="a" href={`${GOOGLE_LOGIN_URL}${location.search}`} primary>
        <Icon name="google" />
        Sign in to seqr
      </Button>
    </div>
  </Segment>
)


LoginError.propTypes = {
  location: PropTypes.object,
  match: PropTypes.object,
}


export default LoginError

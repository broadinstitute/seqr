import React from 'react'
import PropTypes from 'prop-types'
import { Segment, Message, Button, Icon } from 'semantic-ui-react'
import { getOauthLoginProviderUrl } from 'redux/selectors'

import { ANVIL_URL } from 'shared/utils/constants'

const GOOGLE_SETUP_URL = 'https://support.terra.bio/hc/en-us/articles/360029186611-Setting-up-a-Google-account-with-a-non-Google-email'

const ERROR_MESSAGES = {
  anvil_registration: (
    <span>
      Unable to authorize the selected Google user.
      Please register your account in AnVIL by signing in and registering
      at &nbsp;
      <a href={ANVIL_URL} target="_blank" rel="noreferrer">anvil.terra.bio</a>
      .
      <br />
      If you have already registered your account, please log in to AnVIL and confirm
      you have accepted their latest terms of service.
      <br />
      If the email associated with your account is not managed by google,
      follow
      <a href={GOOGLE_SETUP_URL} target="_blank" rel="noreferrer">these instructions </a>
      to register the email with google before registering with AnVIL.
    </span>
  ),
  no_account: 'No seqr account found for the selected user identity',
}

const LoginError = ({ location, match, oauthLoginProviderUrl }) => (
  <Segment textAlign="center" padded="very" basic>
    <Message error compact>
      {ERROR_MESSAGES[match.params.error] || `Unknown error occured: ${match.params.error}`}
    </Message>
    <div>
      <Button as="a" href={`${oauthLoginProviderUrl}${location.search}`} primary>
        <Icon name="google" />
        Sign in to seqr
      </Button>
    </div>
  </Segment>
)

LoginError.propTypes = {
  location: PropTypes.object,
  match: PropTypes.object,
  oauthLoginProviderUrl: PropTypes.string,
}

const mapStateToProps = state => ({
  oauthLoginProviderUrl: getOauthLoginProviderUrl(state),
})

export default connect(mapStateToProps)(LoginError)

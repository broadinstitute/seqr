import React from 'react'
import PropTypes from 'prop-types'
import { Segment, Header, Grid } from 'semantic-ui-react'

import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import { VerticalSpacer } from 'shared/components/Spacers'

export const UserFormContainer = ({ header, subheader, children }) => (
  <Grid>
    <Grid.Column width={5} />
    <Grid.Column width={6}>
      <VerticalSpacer height={80} />
      <Segment padded="very">
        <Header size="large" content={header} subheader={subheader} />
        {children}
      </Segment>
    </Grid.Column>
    <Grid.Column width={5} />
  </Grid>
)

UserFormContainer.propTypes = {
  header: PropTypes.string,
  subheader: PropTypes.string,
  children: PropTypes.node,
}

export const UserForm = props => <ReduxFormWrapper {...props} showErrorPanel noModal />

const UserFormLayout = React.memo(({ header, subheader, children, content, ...formProps }) => (
  <UserFormContainer header={header} subheader={subheader}>
    <UserForm {...formProps} />
  </UserFormContainer>
))

UserFormLayout.propTypes = {
  header: PropTypes.string,
  subheader: PropTypes.string,
  children: PropTypes.node,
  content: PropTypes.node,
}

export default UserFormLayout

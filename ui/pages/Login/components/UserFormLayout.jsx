import React from 'react'
import PropTypes from 'prop-types'
import { Segment, Header, Grid } from 'semantic-ui-react'

import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import { VerticalSpacer } from 'shared/components/Spacers'

const UserFormLayout = ({ header, subheader, ...formProps }) =>
  <Grid>
    <Grid.Column width={5} />
    <Grid.Column width={6}>
      <VerticalSpacer height={80} />
      <Segment padded="very">
        <Header size="large" content={header} subheader={subheader} />
        <ReduxFormWrapper
          {...formProps}
          showErrorPanel
          noModal
        />
      </Segment>
    </Grid.Column>
    <Grid.Column width={5} />
  </Grid>

UserFormLayout.propTypes = {
  header: PropTypes.string,
  subheader: PropTypes.string,
}

export default UserFormLayout

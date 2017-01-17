import React from 'react'
import { Grid } from 'semantic-ui-react'

import Header from './Header'
import Footer from './Footer'

const BaseLayout = ({ user, children }) =>
  <div style={{ height: 'calc(100% - 46px)' }}>
    <Header user={user} />
    <Grid style={{ minHeight: 'calc(100% - 46px)' }}>
      <Grid.Column width={1} />
      <Grid.Column width={14} style={{ marginTop: '30px' }}>
        {children}
      </Grid.Column>
      <Grid.Column width={1} />
    </Grid>
    <Footer />
  </div>


BaseLayout.propTypes = {
  user: React.PropTypes.object.isRequired,
  children: React.PropTypes.element.isRequired,  //require 1 child component
}

export default BaseLayout


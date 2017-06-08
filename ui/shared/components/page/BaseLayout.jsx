/**
 * Top-level page layout that consists of the standard seqr header and footer, with arbitrary
 * content in-between.
 */

import React from 'react'
import PropTypes from 'prop-types'

import { Grid } from 'semantic-ui-react'
import { connect } from 'react-redux'

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

export { BaseLayout as BaseLayoutComponent }

BaseLayout.propTypes = {
  user: PropTypes.object.isRequired,
  children: PropTypes.node,
}


// wrap top-level component so that redux state is passed in as props
const mapStateToProps = ({ user }) => ({ user })

export default connect(mapStateToProps)(BaseLayout)


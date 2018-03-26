/**
 * Top-level page layout that consists of the standard seqr header and footer, with arbitrary
 * content in-between.
 */

import React from 'react'
import PropTypes from 'prop-types'
import { Grid } from 'semantic-ui-react'
import { connect } from 'react-redux'
import { getUser } from 'redux/utils/commonDataActionsAndSelectors'

import Header from './Header'
import PageHeader from './PageHeader'
import Footer from './Footer'


const BaseLayout = ({ user, match, children }) =>
  <div style={{ height: 'calc(100% - 46px)' }}>
    <Header user={user} />
    <Grid style={{ minHeight: 'calc(100% - 46px)' }}>
      {match && match.props.projectGuid && <PageHeader />}
      <Grid.Row>
        <Grid.Column width={1} />
        <Grid.Column width={14}>
          {children}
        </Grid.Column>
        <Grid.Column width={1} />
      </Grid.Row>
    </Grid>
    <Footer />
  </div>

export { BaseLayout as BaseLayoutComponent }

BaseLayout.propTypes = {
  user: PropTypes.object.isRequired,
  match: PropTypes.object,
  children: PropTypes.node,
}


// wrap top-level component so that redux state is passed in as props
const mapStateToProps = state => ({
  user: getUser(state),
})

export default connect(mapStateToProps)(BaseLayout)

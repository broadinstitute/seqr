/**
 * Top-level page layout that consists of the standard seqr header and footer, with arbitrary
 * content in-between.
 */

import React from 'react'
import PropTypes from 'prop-types'
import { Grid } from 'semantic-ui-react'
import { Route } from 'react-router-dom'

import Header from './Header'
import PageHeader from './PageHeader'
import Footer from './Footer'


const BaseLayout = ({ children }) =>
  <div style={{ height: '100%' }}>
    <div style={{ minHeight: 'calc(100% - 20px)', paddingBottom: '40px' }}>
      <Header />
      <Grid>
        <Route path="/project/:projectGuid/:breadcrumb/:breadcrumbId?" component={PageHeader} />
        <PageHeader />
        <Grid.Row>
          <Grid.Column width={1} />
          <Grid.Column width={14}>
            {children}
          </Grid.Column>
          <Grid.Column width={1} />
        </Grid.Row>
      </Grid>
    </div>
    <Footer />
  </div>

export { BaseLayout as BaseLayoutComponent }

BaseLayout.propTypes = {
  children: PropTypes.node,
}

export default BaseLayout

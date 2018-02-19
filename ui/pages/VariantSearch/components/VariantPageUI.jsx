import React from 'react'
/*
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import styled from 'styled-components'
*/
import DocumentTitle from 'react-document-title'
import BaseLayout from 'shared/components/page/BaseLayout'
//import { getProject } from 'shared/utils/redux/commonDataActionsAndSelectors'
import VariantSearchControls from './VariantSearchControls'
import VariantPageHeader from './VariantPageHeader'

import VariantTable from './VariantTable'


const VariantPageUI = () =>
  <BaseLayout pageHeader={<VariantPageHeader />}>
    <DocumentTitle title="seqr: variant search" />
    <VariantSearchControls />
    <VariantTable />
  </BaseLayout>

/*
export { VariantPageUI as VariantPageUIComponent }

VariantPageUI.propTypes = {
  //user: PropTypes.object.isRequired,
  project: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  //user: getUser(state),
  project: getProject(state),
})

export default connect(mapStateToProps)(VariantPageUI)
*/
export default VariantPageUI

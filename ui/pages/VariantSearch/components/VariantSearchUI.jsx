import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import { Grid } from 'semantic-ui-react'
import DocumentTitle from 'react-document-title'

import BaseLayout from 'shared/components/page/BaseLayout'
import { getProject } from 'shared/utils/commonSelectors'


const VariantPageUI = props =>
  <BaseLayout pageHeader={
    <div style={{ margin: '0px 0px 30px 60px' }}>
      <Grid stackable>
        <Grid.Column width={16}>
          <div style={{ fontWeight: 300, fontSize: '36px', margin: '50px 0px 35px 0px' }}>
            Project » <span style={{ fontWeight: 750 }}>{props.project.name}</span>
          </div>
          {
            props.project.description &&
            <div style={{ fontWeight: 300, fontSize: '16px', margin: '0px 30px 20px 0px', display: 'inline-block' }}>
              {props.project.description}
            </div>
          }
        </Grid.Column>
      </Grid>
    </div>}
  >
    <DocumentTitle title="seqr: variant search" />
  </BaseLayout>


export { VariantPageUI as ProjectPageUIComponent }

VariantPageUI.propTypes = {
  //user: PropTypes.object.isRequired,
  project: PropTypes.object.isRequired,
}

const mapStateToProps = state => ({
  //user: getUser(state),
  project: getProject(state),
})

export default connect(mapStateToProps)(VariantPageUI)

import React from 'react'
import PropTypes from 'prop-types'
import { Grid, Message } from 'semantic-ui-react'

import FormWrapper from 'shared/components/form/FormWrapper'

const UploadFormPage = React.memo(({ fields, uploadStats, onSubmit }) => (
  <Grid>
    <Grid.Row>
      <Grid.Column width={4} />
      <Grid.Column width={8}>
        <FormWrapper
          onSubmit={onSubmit}
          fields={fields}
          noModal
          showErrorPanel
        />
      </Grid.Column>
      <Grid.Column width={4} />
    </Grid.Row>
    <Grid.Row>
      <Grid.Column width={4} />
      <Grid.Column width={8}>
        {uploadStats.info?.length > 0 && <Message info list={uploadStats.info} />}
        {uploadStats.warnings?.length > 0 && <Message warning list={uploadStats.warnings} />}
      </Grid.Column>
      <Grid.Column width={4} />
    </Grid.Row>
  </Grid>
))

UploadFormPage.propTypes = {
  fields: PropTypes.arrayOf(PropTypes.object),
  uploadStats: PropTypes.object,
  onSubmit: PropTypes.func,
}

export default UploadFormPage

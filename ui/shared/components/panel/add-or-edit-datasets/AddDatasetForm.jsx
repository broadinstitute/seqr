import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Form, Grid } from 'semantic-ui-react'
import { getProject, getIndividualsByGuid } from 'shared/utils/commonSelectors'
import FormWrapper from 'shared/components/form/FormWrapper'


class AddDatasetForm extends React.PureComponent
{
  static propTypes = {
    //user: PropTypes.object.isRequired,
    project: PropTypes.object,
    handleSave: PropTypes.func,
    handleClose: PropTypes.func,
  }


  constructor(props) {
    super(props)

    this.formDataJson = {}
  }

  render() {

    return (
      <FormWrapper
        cancelButtonText="Cancel"
        submitButtonText="Add"
        performValidation={this.performValidation}
        handleSave={this.props.handleSave}
        handleClose={this.props.handleClose}
        size="large"
        confirmCloseIfNotSaved={false}
        getFormDataJson={() => this.formDataJson}
        formSubmitUrl={`/api/project/${this.props.project.projectGuid}/add_dataset`}
      >
        <Grid>
          <Grid.Row>
            <Grid.Column width={16}>
              <Form.Input
                label="Dataset Path"
                name="path"
                placeholder="local path or gs:// path to Google bucket"
                onChange={(event, data) => {
                  this.formDataJson.path = data.value
                }}
              />
            </Grid.Column>
          </Grid.Row>
          <Grid.Row>
            <Grid.Column width={5}>
              <Form.Dropdown
                style={{ height: '35px', padding: '10px 15px' }}
                label="Sample Type"
                name="sample_type"
                onChange={(event, data) => {
                  this.formDataJson.sample_type = data.value
                }}
                fluid
                selection
                placeholder="select sample type"
                options={
                  [
                    { key: 'WES', value: 'WES', text: 'Exome' },
                    { key: 'WGS', value: 'WGS', text: 'Whole Genome' },
                    { key: 'RNA', value: 'RNA', text: 'RNA-seq' },
                  ]
                }
              />
            </Grid.Column>
            <Grid.Column width={6}>
              <Form.Dropdown
                style={{ height: '37px', padding: '10px 15px' }}
                label="Analysis Type"
                name="analysis_type"
                onChange={(event, data) => {
                  this.formDataJson.analysis_type = data.value
                }}
                fluid
                selection
                placeholder="select analysis type"
                options={
                  [
                    { key: 'VARIANTS-GATK', value: 'VARIANTS-GATK', text: 'Variant Callset - GATK' },
                    { key: 'VARIANTS-OTHER', value: 'VARIANTS-OTHER', text: 'Variant Callset - Other' },
                    { key: 'SV-MANTA', value: 'SV-MANTA', text: 'SV Callset - Manta' },
                    { key: 'SV-OTHER', value: 'SV-OTHER', text: 'SV Callset - Other' },
                  ]
                }
              />
            </Grid.Column>
            <Grid.Column width={5}>
              <Form.Dropdown
                style={{ height: '37px', padding: '10px 15px' }}
                label="Genome Version"
                name="genome_version"
                onChange={(event, data) => {
                  this.formDataJson.genome_version = data.value
                }}
                fluid
                selection
                placeholder="select genome version"
                options={
                  [
                    { key: 'GRCH37', value: 'GRCH37', text: 'hg19 / GRCh37' },
                    { key: 'GRCH38', value: 'GRCH38', text: 'hg38 / GRCh38' },
                  ]
                }
              />
            </Grid.Column>
          </Grid.Row>
          <Grid.Row />
        </Grid>
      </FormWrapper>)
  }

  performValidation = (formData) => {
    if (!formData.sample_type) {
      return { errors: ['sample type not selected'] }
    }
    if (!formData.analysis_type) {
      return { errors: ['analysis type not selected'] }
    }
    if (!formData.genome_version) {
      return { errors: ['analysis type not selected'] }
    }
    if (!formData.path) {
      return { errors: ['dataset path not specified'] }
    }

    return {}
  }
}

export { AddDatasetForm as AddDatasetFormComponent }

const mapStateToProps = state => ({
  project: getProject(state),
  individualsByGuid: getIndividualsByGuid(state),
})

export default connect(mapStateToProps)(AddDatasetForm)

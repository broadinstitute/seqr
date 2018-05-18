/* eslint-disable jsx-a11y/label-has-for */

import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Form, Grid, Popup, Icon } from 'semantic-ui-react'
import styled from 'styled-components'
import { getProject } from 'pages/Project/selectors'
import FormWrapper from 'shared/components/form/FormWrapper'


const StyledLabel = styled.label`
  font-weight: 700;
  display: inline-block !important;
  padding-right: 20px;
`

const StyledIcon = styled(Icon)`
  color: #888888;
`

const SAMPLE_TYPES = [
  { key: 'WES', value: 'WES', text: 'Exome' },
  { key: 'WGS', value: 'WGS', text: 'Genome' },
  { key: 'RNA', value: 'RNA', text: 'RNA-seq' },
]

const GENOME_VERSIONS = [
  { key: 'GRCH37', value: 'GRCH37', text: 'GRCh37' },
  { key: 'GRCH38', value: 'GRCH38', text: 'GRCh38' },
]

class AddLoadedCallsetForm extends React.PureComponent
{
  static propTypes = {
    //user: PropTypes.object.isRequired,
    project: PropTypes.object,
    handleSave: PropTypes.func,
    handleClose: PropTypes.func,
  }


  constructor(props) {
    super(props)

    this.formDataJson = {
      datasetType: 'ALIGN',
    }
  }

  render() {

    return (
      <FormWrapper
        submitButtonText="Add"
        performClientSideValidation={this.performValidation}
        handleSave={this.props.handleSave}
        handleClose={this.props.handleClose}
        size="small"
        confirmCloseIfNotSaved={false}
        getFormDataJson={() => this.formDataJson}
        formSubmitUrl={`/api/project/${this.props.project.projectGuid}/add_dataset`}
      >
        <Grid>
          <Grid.Row>
            <Grid.Column width={5}>
              <Form.Field>
                <StyledLabel>Sample Type</StyledLabel>
                <Popup
                  trigger={<StyledIcon name="question circle outline" />}
                  content="Biological sample type"
                  size="small"
                  position="top center"
                />
                <Form.Dropdown
                  name="sample_type"
                  onChange={(event, data) => {
                    this.formDataJson.sampleType = data.value
                  }}
                  fluid
                  selection
                  placeholder="select sample type"
                  options={SAMPLE_TYPES}
                />
              </Form.Field>
            </Grid.Column>
            <Grid.Column width={5}>
              <Form.Field>
                <StyledLabel>Genome Version</StyledLabel>
                <Popup
                  trigger={<StyledIcon name="question circle outline" />}
                  content="The reference genome assembly used for this dataset"
                  size="small"
                  position="top center"
                />

                <Form.Dropdown
                  name="genome_version"
                  onChange={(event, data) => {
                    this.formDataJson.genomeVersion = data.value
                  }}
                  fluid
                  selection
                  placeholder="select genome version"
                  options={GENOME_VERSIONS}
                />
              </Form.Field>
            </Grid.Column>
          </Grid.Row>
          <Grid.Row>
            <Grid.Column width={16}>
              <Form.Field>
                <StyledLabel>BAM or CRAM table path</StyledLabel>
                <Popup
                  trigger={<StyledIcon name="question circle outline" />}
                  content={
                    <div>
                      BAM or CRAM table path - path of file that maps seqr Individual Ids to their BAM or CRAM file path. <br />
                      <br />
                      <b>File Format:</b><br />
                      Tab-separated text file (.tsv) or Excel spreadsheet (.xls)<br />
                      <b>Column 1:</b> Individual ID <br />
                      <b>Column 2:</b> gs:// Google bucket path or server filesystem path of the BAM or CRAM file for this Individual<br />
                    </div>
                  }
                  size="small"
                  position="top center"
                />

                <Form.Input
                  name="table_path"
                  placeholder="gs:// Google bucket path or server filesystem path of the BAM / CRAM table"
                  onChange={(event, data) => {
                    this.formDataJson.datasetPath = data.value
                  }}
                />
              </Form.Field>
            </Grid.Column>
          </Grid.Row>
          <Grid.Row />
        </Grid>
      </FormWrapper>)
  }

  performValidation = (formData) => {
    if (!formData.sampleType) {
      return { errors: ['Sample Type not selected'] }
    }
    if (!formData.genomeVersion) {
      return { errors: ['Genome Version not selected'] }
    }
    if (!formData.datasetPath) {
      return { errors: ['Table Path not specified'] }
    }

    return {}
  }
}

export { AddLoadedCallsetForm as AddLoadedCallsetFormComponent }

const mapStateToProps = state => ({
  project: getProject(state),
})

export default connect(mapStateToProps)(AddLoadedCallsetForm)

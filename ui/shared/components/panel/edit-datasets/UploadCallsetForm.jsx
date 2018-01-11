/* eslint-disable jsx-a11y/label-has-for */

import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Form, Grid, Popup, Icon } from 'semantic-ui-react'
import styled from 'styled-components'
import { getProject, getIndividualsByGuid } from 'shared/utils/redux/commonDataActionsAndSelectors'
import FormWrapper from 'shared/components/form/FormWrapper'


const StyledLabel = styled.label`
  font-weight: 700;
  display: inline-block !important;
  padding-right: 20px;
`

const StyledIcon = styled(Icon)`
  color: #888888;
  padding-right: 20px;
`

class UploadCallsetForm extends React.PureComponent
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
      datasetType: 'VARIANTS',
    }
  }

  render() {

    return (
      <FormWrapper
        submitButtonText="Upload"
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
            <Grid.Column width={6}>
              <StyledLabel>Name</StyledLabel>
              <Popup
                trigger={<StyledIcon name="question circle outline" />}
                content="Callset name"
                size="small"
                position="top center"
              />
              (Optional)
              <div>
                <Form.Input
                  name="name"
                  placeholder=""
                  onChange={(event, data) => {
                    this.formDataJson.name = data.value
                  }}
                />
              </div>
            </Grid.Column>
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
                  style={{ height: '35px', padding: '10px 15px' }}
                  name="sample_type"
                  onChange={(event, data) => {
                    this.formDataJson.sampleType = data.value
                  }}
                  fluid
                  selection
                  placeholder="select sample type"
                  options={
                    [
                      { key: 'WES', value: 'WES', text: 'Exome' },
                      { key: 'WGS', value: 'WGS', text: 'Genome' },
                      { key: 'RNA', value: 'RNA', text: 'RNA-seq' },
                    ]
                  }
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
                  style={{ height: '37px', padding: '10px 15px' }}
                  name="genome_version"
                  onChange={(event, data) => {
                    this.formDataJson.genomeVersion = data.value
                  }}
                  fluid
                  selection
                  placeholder="select genome version"
                  options={
                    [
                      { key: 'GRCH37', value: 'GRCH37', text: 'GRCh37' },
                      { key: 'GRCH38', value: 'GRCH38', text: 'GRCh38' },
                    ]
                  }
                />
              </Form.Field>
            </Grid.Column>
          </Grid.Row>
          <Grid.Row>
            <Grid.Column width={16}>
              <StyledLabel>Description</StyledLabel>
              <Popup
                trigger={<StyledIcon name="question circle outline" />}
                content="Callset description"
                size="small"
                position="top center"
              />
              (Optional)
              <Form.Input
                name="description"
                placeholder=""
                onChange={(event, data) => {
                  this.formDataJson.description = data.value
                }}
              />
            </Grid.Column>
          </Grid.Row>
          <Grid.Row>
            <Grid.Column width={16}>
              <Form.Field>
                <StyledLabel>Callset Path</StyledLabel>
                <Popup
                  trigger={<StyledIcon name="question circle outline" />}
                  content="Callset path either on the server filesystem or on Google cloud storage. The file can be a compressed VCF (*.vcf.gz), or a hail VDS file."
                  size="small"
                  position="top center"
                />
                <Form.Input
                  name="dataset_path"
                  placeholder="gs:// Google bucket path or server filesystem path"
                  onChange={(event, data) => {
                    this.formDataJson.datasetPath = data.value
                  }}
                />
              </Form.Field>
              <Form.Field style={{ display: 'flex', alignItems: 'center', paddingTop: '15px' }}>
                <input
                  type="checkbox"
                  onChange={(e) => {
                    const isChecked = e.target.checked
                    this.formDataJson.ignoreExtraSamplesInCallset = isChecked
                  }}
                />
                <div style={{ padding: '0 20px 0 10px' }}>Ignore extra samples in callset</div>
                <Popup
                  trigger={<StyledIcon name="question circle outline" />}
                  content="If the callset contains sample ids that don't match individuals in this project, ignore them instead of reporting an error."
                  size="small"
                  position="top center"
                />
              </Form.Field>
            </Grid.Column>
          </Grid.Row>
          <Grid.Row>
            <Grid.Column width={16}>
              <Form.Field>
                <StyledLabel>
                  Sample ID To Individual ID Mapping
                </StyledLabel>
                <StyledLabel>
                  <Popup
                    trigger={<StyledIcon name="question circle outline" />}
                    content={
                      <div>
                        Path of file that maps VCF Sample Ids to their corresponding seqr Individual Ids. <br />
                        <br />
                        <b>File Format:</b><br />
                        Tab-separated text file (.tsv) or Excel spreadsheet (.xls)<br />
                        <b>Column 1:</b> Sample ID <br />
                        <b>Column 2:</b> Individual ID <br />
                      </div>
                    }
                    size="small"
                    position="top center"
                  />
                </StyledLabel>
                (Optional)
                <Form.Input
                  name="sample_id_mapping_file"
                  placeholder="gs:// Google bucket path or server filesystem path"
                  onChange={(event, data) => {
                    this.formDataJson.sampleIdsToIndividualIdsPath = data.value
                  }}
                />
              </Form.Field>
            </Grid.Column>
          </Grid.Row>
          <Grid.Row>
            <Grid.Column width={6}>
              <StyledLabel>Elasticsearch Index</StyledLabel>
              <Popup
                trigger={<StyledIcon name="question circle outline" />}
                content="If the callset has already been loaded, the elasticsearch index can be specified here in order to skip running the loading pipeline."
                size="small"
                position="top center"
              />
              (Optional)
              <Form.Input
                name="elasticsearch_index"
                placeholder=""
                onChange={(event, data) => {
                  this.formDataJson.elasticsearchIndex = data.value
                }}
              />
            </Grid.Column>
          </Grid.Row>
          <Grid.Row />
        </Grid>
      </FormWrapper>)
  }

  performValidation = (formData) => {
    if (!formData.sampleType) {
      return { errors: [' please set the Sample Type'] }
    }
    if (!formData.genomeVersion) {
      return { errors: [' please set the Genome Version'] }
    }
    if (!formData.datasetPath) {
      return { errors: [' please specify the Callset Path'] }
    }

    return {}
  }
}

export { UploadCallsetForm as UploadCallsetFormComponent }

const mapStateToProps = state => ({
  project: getProject(state),
  individualsByGuid: getIndividualsByGuid(state),
})

export default connect(mapStateToProps)(UploadCallsetForm)

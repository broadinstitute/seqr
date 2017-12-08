/* eslint-disable jsx-a11y/label-has-for */

import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Form, Grid, Popup, Icon } from 'semantic-ui-react'
import styled from 'styled-components'
import { getProject, getIndividualsByGuid } from 'shared/utils/commonSelectors'
import FormWrapper from 'shared/components/form/FormWrapper'


const StyledLabel = styled.label`
  font-weight: 700;
  display: inline-block !important;
  padding-right: 20px;
`

const StyledIcon = styled(Icon)`
  color: #888888;
`

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
      datasetType: 'VARIANTS',
    }
  }

  render() {

    return (
      <FormWrapper
        submitButtonText="Add"
        performValidation={this.performValidation}
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
              <Form.Field>
                <StyledLabel>Elasticsearch Index</StyledLabel>
                <Popup
                  trigger={<StyledIcon name="question circle outline" />}
                  content="The Elasticsearch index that contains this dataset"
                  size="small"
                  position="top center"
                />
                <Form.Input
                  name="elasticsearch_index"
                  onChange={(event, data) => {
                    this.formDataJson.elasticsearchIndex = data.value
                  }}
                  placeholder=""
                />
              </Form.Field>
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
                      { key: 'WGS', value: 'WGS', text: 'Whole Genome' },
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
                      { key: 'GRCH37', value: 'GRCH37', text: 'GRCh37 / hg19' },
                      { key: 'GRCH38', value: 'GRCH38', text: 'GRCh38' },
                    ]
                  }
                />
              </Form.Field>
            </Grid.Column>
          </Grid.Row>
          <Grid.Row>
            <Grid.Column width={16}>
              <Form.Field>
                <StyledLabel>VCF Path</StyledLabel>
                <Popup
                  trigger={<StyledIcon name="question circle outline" />}
                  content="Compressed VCF (*.vcf.gz) file path on the server or on Google cloud storage."
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
                        Optional - path of file that maps VCF Sample Ids to their corresponding seqr Individual Ids. <br />
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
          <Grid.Row />
        </Grid>
      </FormWrapper>)
  }

  performValidation = (formData) => {
    if (!formData.elasticsearchIndex) {
      return { errors: ['Elasticsearch index not specified'] }
    }
    if (!formData.sampleType) {
      return { errors: ['Elasticsearch dataset not specified'] }
    }
    if (!formData.sampleType) {
      return { errors: ['Sample Type not selected'] }
    }
    if (!formData.genomeVersion) {
      return { errors: ['Genome Version not selected'] }
    }
    if (!formData.datasetPath) {
      return { errors: ['VCF Path not specified'] }
    }

    return {}
  }
}

export { AddLoadedCallsetForm as AddLoadedCallsetFormComponent }

const mapStateToProps = state => ({
  project: getProject(state),
  individualsByGuid: getIndividualsByGuid(state),
})

export default connect(mapStateToProps)(AddLoadedCallsetForm)

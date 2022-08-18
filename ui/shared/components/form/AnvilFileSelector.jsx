import React from 'react'
import PropTypes from 'prop-types'
import { Message } from 'semantic-ui-react'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { Select } from 'shared/components/form/Inputs'
import { FormSpy } from 'react-final-form'
import DataLoader from '../DataLoader'

class AnvilFileSelector extends React.PureComponent {

  static propTypes = {
    namespace: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
  }

  state = {
    dataPathList: null,
    loading: false,
    errorHeader: null,
    error: null,
  }

  load = () => {
    const { namespace, name } = this.props
    this.setState({ loading: true })
    new HttpRequestHelper(`/api/create_project_from_workspace/${namespace}/${name}/get_vcf_list`,
      (responseJson) => {
        this.setState({ loading: false, dataPathList: responseJson.dataPathList })
        if (responseJson.dataPathList?.length === 0) {
          this.setState({
            errorHeader: 'No joint called VCF found in workspace',
            error: 'There are no joint called VCFs in the Files section of this workspace. VCFs must have a .vcf, .vcf.gz, or .vcf.bgz file extension. Please add a VCF to your workspace before proceeding with loading.',
          })
        }
      },
      (e) => {
        this.setState({ loading: false, errorHeader: 'Error loading workspace files', error: e.message })
      }).get()
  }

  render() {
    const { dataPathList, loading, errorHeader, error } = this.state
    const options = dataPathList?.map(file => ({ name: file, value: file }))
    const errorMessage = error ? <Message visible error header={errorHeader} content={error} /> : null
    return (
      <DataLoader content={dataPathList} loading={loading} load={this.load} errorMessage={errorMessage}>
        <Select {...this.props} options={options} />
      </DataLoader>
    )
  }

}

const SUBSCRIPTION = { values: true }

export default props => (
  <FormSpy subscription={SUBSCRIPTION}>
    {({ values }) => (
      <AnvilFileSelector {...props} namespace={values.workspaceNamespace} name={values.workspaceName} />
    )}
  </FormSpy>
)

import React from 'react'
import PropTypes from 'prop-types'

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
  }

  load = () => {
    const { namespace, name } = this.props
    this.setState({ loading: true })
    new HttpRequestHelper(`/api/create_project_from_workspace/${namespace}/${name}/get_vcf_list`,
      (responseJson) => {
        this.setState({ loading: false, dataPathList: responseJson.dataPathList || [] })
      },
      (e) => {
        this.setState({ loading: false, dataPathList: [e.message] })
      }).get()
  }

  render() {
    const { dataPathList, loading } = this.state
    const options = dataPathList?.map(file => ({ name: file, value: file })) || []
    return (
      <DataLoader content={dataPathList} loading={loading} load={this.load}>
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

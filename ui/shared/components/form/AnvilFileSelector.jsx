import React from 'react'
import PropTypes from 'prop-types'
import { FormSpy } from 'react-final-form'
import LoadOptionsSelect from './LoadOptionsSelect'

const AnvilFileSelector = ({ namespace, name, ...props }) => (
  <LoadOptionsSelect
    url={`/api/create_project_from_workspace/${namespace}/${name}/get_vcf_list`}
    optionsResponseKey="dataPathList"
    errorHeader="Error loading workspace files"
    validationErrorHeader="No joint called VCF found in workspace"
    validationErrorMessage="There are no joint called VCFs in the Files section of this workspace. VCFs must have a .vcf, .vcf.gz, or .vcf.bgz file extension. Please add a VCF to your workspace before proceeding with loading."
    {...props}
  />
)

AnvilFileSelector.propTypes = {
  namespace: PropTypes.string.isRequired,
  name: PropTypes.string.isRequired,
}

const SUBSCRIPTION = { values: true }

export default props => (
  <FormSpy subscription={SUBSCRIPTION}>
    {({ values }) => (
      <AnvilFileSelector {...props} namespace={values.workspaceNamespace} name={values.workspaceName} />
    )}
  </FormSpy>
)

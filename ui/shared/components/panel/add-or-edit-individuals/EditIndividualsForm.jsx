import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getProject, getIndividualsByGuid } from 'shared/utils/commonSelectors'
import FormWrapper from 'shared/components/form/FormWrapper'


class EditIndividualsForm extends React.PureComponent
{
  static propTypes = {
    //user: PropTypes.object.isRequired,
    individualsByGuid: PropTypes.object.isRequired,
    //project: PropTypes.object,
    handleSave: PropTypes.func,
    handleClose: PropTypes.func,
  }

  //constructor(props) {
  //  super(props)
  //}

  render() {

    return (
      <FormWrapper
        cancelButtonText="Cancel"
        submitButtonText="Apply"
        performValidation={this.performValidation}
        handleSave={this.props.handleSave}
        handleClose={this.props.handleClose}
        size="large"
        confirmCloseIfNotSaved
        getFormDataJson={() => {}}
      >
        {
          Object.keys(this.props.individualsByGuid).map(individualGuid =>
            <input key={individualGuid} type="text" defaultValue={individualGuid} />,
          )
        }
      </FormWrapper>)
  }

  performValidation = () => {
    return { errors: [], warnings: [], info: [] }
  }
}

export { EditIndividualsForm as EditIndividualsFormComponent }

const mapStateToProps = state => ({
  project: getProject(state),
  individualsByGuid: getIndividualsByGuid(state),
})

export default connect(mapStateToProps)(EditIndividualsForm)

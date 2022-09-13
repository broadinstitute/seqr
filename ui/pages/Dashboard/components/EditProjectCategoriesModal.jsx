import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { Multiselect } from 'shared/components/form/Inputs'
import OptionFieldView from 'shared/components/panel/view-fields/OptionFieldView'

import { updateProject } from 'redux/rootReducer'

import { getEditableCategoryOptions } from '../selectors'

const FIELD_PROPS = {
  component: Multiselect,
  allowAdditions: true,
  additionLabel: 'Category: ',
  placeholder: 'Project categories',
  color: 'blue',
}

const EditProjectCategoriesModal = React.memo(({ project, categories, trigger, triggerName, popup, onSubmit }) => (
  <OptionFieldView
    field="projectCategoryGuids"
    idField="projectGuid"
    tagOptions={categories}
    formFieldProps={FIELD_PROPS}
    initialValues={project}
    isEditable
    simplifiedValue
    hideValue
    modalTrigger={trigger}
    modalPopup={popup}
    modalTitle="Edit Project Categories"
    modalId={triggerName}
    onSubmit={onSubmit}
  />
))

EditProjectCategoriesModal.propTypes = {
  trigger: PropTypes.node,
  project: PropTypes.object,
  categories: PropTypes.arrayOf(PropTypes.object),
  onSubmit: PropTypes.func,
  popup: PropTypes.object,
  triggerName: PropTypes.string,
}

const mapStateToProps = state => ({
  categories: getEditableCategoryOptions(state),
})

const mapDispatchToProps = {
  onSubmit: values => updateProject({ ...values, projectField: 'categories' }),
}

export { EditProjectCategoriesModal as EditProjectCategoriesModalComponent }
export default connect(mapStateToProps, mapDispatchToProps)(EditProjectCategoriesModal)

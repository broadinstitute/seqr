import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import { Multiselect } from 'shared/components/form/Inputs'
import Modal from 'shared/components/modal/Modal'

import { updateProject } from 'redux/rootReducer'
import { getProjectCategoriesByGuid } from 'redux/selectors'


const EditProjectCategoriesModal = (props) => {
  const categories = Object.values(props.projectCategoriesByGuid).map((projectCategory) => {
    return { value: projectCategory.guid, text: projectCategory.name }
  })
  const formName = `editProjectCategories-${props.project.projectGuid}-${props.triggerName}`
  const fields = [
    {
      name: 'categories',
      options: categories,
      component: Multiselect,
      allowAdditions: true,
      additionLabel: 'Category: ',
      placeholder: 'Project categories',
      color: 'blue',
    },
  ]
  const initialValues = {
    categories: props.project.projectCategoryGuids,
    projectGuid: props.project.projectGuid,
    projectField: 'categories',
  }
  return (
    <Modal trigger={props.trigger} popup={props.popup} title="Edit Project Categories" modalName={formName}>
      <ReduxFormWrapper
        initialValues={initialValues}
        onSubmit={props.updateProject}
        form={formName}
        fields={fields}
      />
    </Modal>
  )
}

EditProjectCategoriesModal.propTypes = {
  trigger: PropTypes.node,
  project: PropTypes.object,
  projectCategoriesByGuid: PropTypes.object,
  updateProject: PropTypes.func,
  popup: PropTypes.object,
  triggerName: PropTypes.string,
}

const mapStateToProps = state => ({
  projectCategoriesByGuid: getProjectCategoriesByGuid(state),
})

const mapDispatchToProps = {
  updateProject,
}

export { EditProjectCategoriesModal as EditProjectCategoriesModalComponent }
export default connect(mapStateToProps, mapDispatchToProps)(EditProjectCategoriesModal)

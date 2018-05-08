import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import { Multiselect } from 'shared/components/form/Inputs'
import Modal from 'shared/components/modal/Modal'

import { updateProject, getProjectCategoriesByGuid } from 'redux/rootReducer'


const EditProjectCategoriesModal = (props) => {
  const categories = Object.values(props.projectCategoriesByGuid).map((projectCategory) => {
    return { value: projectCategory.guid, text: projectCategory.name, key: projectCategory.guid }
  })
  const formName = `editProjectCategories-${props.project.projectGuid}`
  return (
    <Modal trigger={props.trigger} popup={props.popup} title="Edit Project Categories" modalName={formName}>
      <ReduxFormWrapper
        initialValues={{
          categories: props.project.projectCategoryGuids,
          projectGuid: props.project.projectGuid,
          projectField: 'categories',
        }}
        onSubmit={props.updateProject}
        form={formName}
        fields={[
          {
            name: 'categories',
            options: categories,
            component: Multiselect,
            additionLabel: 'Category: ',
            placeholder: 'Project categories',
            color: 'blue',
          },
        ]}
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
}

const mapStateToProps = state => ({
  projectCategoriesByGuid: getProjectCategoriesByGuid(state),
})

const mapDispatchToProps = {
  updateProject,
}

export { EditProjectCategoriesModal as EditProjectCategoriesModalComponent }
export default connect(mapStateToProps, mapDispatchToProps)(EditProjectCategoriesModal)

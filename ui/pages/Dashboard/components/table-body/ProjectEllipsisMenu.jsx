import React from 'react'
import PropTypes from 'prop-types'
import { Dropdown, Icon, Form } from 'semantic-ui-react'
import { connect } from 'react-redux'

import { updateProject } from 'redux/rootReducer'
import { computeCaseReviewUrl } from 'shared/utils/urlUtils'
import ReduxFormWrapper from 'shared/components/form/ReduxFormWrapper'
import Modal from 'shared/components/modal/Modal'
import { EDIT_NAME_MODAL, EDIT_DESCRIPTION_MODAL } from '../../constants'


const ProjectEllipsisMenu = props =>
  <span className="ellipsis-menu">{
    <Dropdown pointing="top right" icon={
      <Icon name="ellipsis vertical" />}
    >
      <Dropdown.Menu>
        {props.user.is_staff && [
          <Dropdown.Item key={1} onClick={() => { window.open(computeCaseReviewUrl(props.project.projectGuid), '_blank') }}>
            Case Review Page
          </Dropdown.Item>,
          <Dropdown.Divider key={2} />,
        ]}

        {(props.user.is_staff || props.project.canEdit) && [
          <Modal key={1} trigger={<Dropdown.Item>Edit Name</Dropdown.Item>} title="Edit Project Name">
            <ReduxFormWrapper
              initialValues={{ name: props.project.name, projectGuid: props.project.projectGuid }}
              onSubmit={props.updateProject}
              {...EDIT_NAME_MODAL}
            />
          </Modal>,
          <Modal key={2} trigger={<Dropdown.Item>Edit Description</Dropdown.Item>} title="Edit Project Description">
            <ReduxFormWrapper
              initialValues={{ description: props.project.description, projectGuid: props.project.projectGuid }}
              onSubmit={props.updateProject}
              {...EDIT_DESCRIPTION_MODAL}
            />
          </Modal>,
          <Modal key={3} trigger={<Dropdown.Item>Edit Categories</Dropdown.Item>} title="Edit Project Categories">
            <ReduxFormWrapper
              initialValues={{ categories: props.project.projectCategoryGuids, projectGuid: props.project.projectGuid }}
              onSubmit={v => console.log(v)}
              form="editProjectCategories"
              fields={[
                {
                  name: 'categories',
                  component: Form.Select,
                  allowAdditions: true,
                  fluid: true,
                  multiple: true,
                  search: true,
                  selection: true,
                  noResultsMessage: null,
                  additionLabel: 'Category: ',
                  tabIndex: '0',
                  /* eslint-disable */
                  options: [{"value":"PC000012_cmg","text":"CMG","key":"PC000012_cmg"},{"value":"PC000013_demo","text":"Demo","key":"PC000013_demo"},{"value":"PC000017_zaheer","text":"Zaheer","key":"PC000017_zaheer"},{"value":"PC000018_lynn","text":"Lynn","key":"PC000018_lynn"},{"value":"PC000019_monica","text":"Monica","key":"PC000019_monica"},{"value":"PC000020_liwen","text":"Liwen","key":"PC000020_liwen"},{"value":"PC000021_katherine","text":"Katherine","key":"PC000021_katherine"},{"value":"PC000022_sam","text":"Sam","key":"PC000022_sam"},{"value":"PC000023_gmkf","text":"GMKF","key":"PC000023_gmkf"},{"value":"PC000025_anne","text":"Anne","key":"PC000025_anne"},{"value":"PC000026_eleina","text":"Eleina","key":"PC000026_eleina"}],
                  placeholder: 'Project categories',
                }
              ]}
            />
          </Modal>,

          <Dropdown.Divider key={4} />,

          <Dropdown.Item key={5} onClick={() => (window.open(`/project/${props.project.deprecatedProjectId}/collaborators`))}>
            Edit Collaborators
          </Dropdown.Item>,
          <Dropdown.Item key={6} onClick={() => (window.open(`/project/${props.project.deprecatedProjectId}/edit-individuals`))}>
            Edit Individuals
          </Dropdown.Item>,
          <Dropdown.Item key={7} onClick={() => (window.open(`/project/${props.project.deprecatedProjectId}/project_gene_list_settings`))}>
            Edit Gene Lists
          </Dropdown.Item>,
        ]}

        {props.user.is_staff && [
          <Dropdown.Divider key={1} />,
          <Modal key={2} trigger={<Dropdown.Item>Delete Project</Dropdown.Item>} title="Delete Project?">
            <ReduxFormWrapper
              initialValues={{ projectGuid: props.project.projectGuid, delete: true }}
              onSubmit={props.updateProject}
              form="deleteProject"
              submitButtonText="Yes"
            >
              <div style={{ textAlign: 'left' }}>Are you sure you want to delete project <b>{props.project.name}</b>?</div>
            </ReduxFormWrapper>
          </Modal>,
        ]}
      </Dropdown.Menu>
    </Dropdown>
  }
  </span>


export { ProjectEllipsisMenu as ProjectEllipsisMenuComponent }


ProjectEllipsisMenu.propTypes = {
  user: PropTypes.object.isRequired,
  project: PropTypes.object.isRequired,
  updateProject: PropTypes.func.isRequired,
}

const mapStateToProps = state => ({ user: state.user })

const mapDispatchToProps = { updateProject }

export default connect(mapStateToProps, mapDispatchToProps)(ProjectEllipsisMenu)

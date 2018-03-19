import { createSingleObjectReducer } from 'redux/utils/reducerUtils'

// actions
const UPDATE_EDIT_PROJECT_MODAL = 'UPDATE_EDIT_PROJECT_MODAL'

// action creators
export const showEditProjectModal = project => ({ type: UPDATE_EDIT_PROJECT_MODAL, updates: { isVisible: true, project } })
export const hideEditProjectModal = () => ({ type: UPDATE_EDIT_PROJECT_MODAL, updates: { isVisible: false } })

//selectors
export const getEditProjectModalIsVisible = state => state.editProjectModal.isVisible
export const getEditProjectModalProject = state => state.editProjectModal.project


const defaultState = {
  isVisible: false,
  project: null,
}

export const editProjectModalState = {
  editProjectModal: createSingleObjectReducer(UPDATE_EDIT_PROJECT_MODAL, defaultState, false),
}

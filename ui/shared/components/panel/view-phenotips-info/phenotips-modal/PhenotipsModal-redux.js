import { createSingleObjectReducer } from 'redux/utils/reducerUtils'

// actions
const UPDATE_PHENOTIPS_MODAL = 'UPDATE_PHENOTIPS_MODAL'

// action creators
export const showPhenotipsModal = (project, individual, isViewOnly) => (
  { type: UPDATE_PHENOTIPS_MODAL, updates: { isVisible: true, project, individual, isViewOnly } }
)
export const hidePhenotipsModal = () => ({ type: UPDATE_PHENOTIPS_MODAL, updates: { isVisible: false } })

//selectors
export const getPhenotipsModalIsVisible = state => state.phenotipsModal.isVisible
export const getPhenotipsModalProject = state => state.phenotipsModal.project
export const getPhenotipsModalIndividual = state => state.phenotipsModal.individual
export const getPhenotipsModalIsViewOnly = state => state.phenotipsModal.isViewOnly

//state
const defaultState = {
  isVisible: false,
  project: null,
  individual: null,
  isViewOnly: true,
}

export const phenotipsModalState = {
  phenotipsModal: createSingleObjectReducer(UPDATE_PHENOTIPS_MODAL, defaultState, false),
}

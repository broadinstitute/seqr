import { createSingleObjectReducer } from 'shared/utils/reducerUtils'

// actions
const UPDATE_PHENOTIPS_MODAL = 'UPDATE_PHENOTIPS_MODAL'

// action creators
export const showPhenotipsModal = (project, individual) => ({ type: UPDATE_PHENOTIPS_MODAL, updates: { isVisible: true, project, individual } })
export const hidePhenotipsModal = () => ({ type: UPDATE_PHENOTIPS_MODAL, updates: { isVisible: false } })

//selectors
export const getPhenotipsModalIsVisible = state => state.phenoTipsModal.isVisible
export const getPhenotipsModalProject = state => state.phenoTipsModal.project
export const getPhenotipsModalIndividual = state => state.phenoTipsModal.individual

//state
const defaultState = {
  isVisible: false,
  project: null,
  individual: null,
}

export const phenoTipsModalState = {
  phenoTipsModal: createSingleObjectReducer(UPDATE_PHENOTIPS_MODAL, defaultState, true),
}

import { createSingleObjectReducer } from 'redux/utils/reducerUtils'

// actions
const UPDATE_EDIT_INDIVIDUALS_MODAL = 'UPDATE_EDIT_INDIVIDUALS_MODAL'


// action creators
export const showEditFamiliesAndIndividualsModal = () => (
  { type: UPDATE_EDIT_INDIVIDUALS_MODAL, updates: { isVisible: true } }
)
export const hideEditFamiliesAndIndividualsModal = () => ({ type: UPDATE_EDIT_INDIVIDUALS_MODAL, updates: { isVisible: false } })

//selectors
export const getEditFamiliesAndIndividualsModalIsVisible = state => state.addOrEditIndividualsModal.isVisible

//state
const defaultState = {
  isVisible: false,
}

export const addOrEditIndividualsModalState = {
  addOrEditIndividualsModal: createSingleObjectReducer(UPDATE_EDIT_INDIVIDUALS_MODAL, defaultState, true),
}


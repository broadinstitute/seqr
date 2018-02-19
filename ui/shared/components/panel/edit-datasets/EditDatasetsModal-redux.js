import { createSingleObjectReducer } from 'shared/utils/redux/reducerUtils'

// actions
const UPDATE_EDIT_DATASETS_MODAL = 'UPDATE_EDIT_DATASETS_MODAL'

// action creators
export const showEditDatasetsModal = () => (
  { type: UPDATE_EDIT_DATASETS_MODAL, updates: { isVisible: true } }
)
export const hideEditDatasetsModal = () => ({ type: UPDATE_EDIT_DATASETS_MODAL, updates: { isVisible: false } })

//selectors
export const getEditDatasetsModalIsVisible = state => state.addOrEditDatasetsModal.isVisible

//state
const defaultState = {
  isVisible: false,
}

export const addOrEditDatasetsModalState = {
  addOrEditDatasetsModal: createSingleObjectReducer(UPDATE_EDIT_DATASETS_MODAL, defaultState, true),
}


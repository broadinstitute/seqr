import { createObjectsByIdReducer } from './reducerFactories'


// actions
const UPDATE_MODAL_STATE = 'UPDATE_MODAL_STATE'

// action creators
export const openModal = modalName => dispatch =>
  dispatch({ type: UPDATE_MODAL_STATE, updatesById: { [modalName]: { open: true } } })
export const closeModal = modalName => dispatch =>
  dispatch({ type: UPDATE_MODAL_STATE, updatesById: { [modalName]: { open: false } } })

// root reducer
export default {
  modal: createObjectsByIdReducer(UPDATE_MODAL_STATE, { open: false, confirmOnClose: null }),
}

// basic selectors
export const getModalOpen = (state, modalName) => state.modal[modalName] && state.modal[modalName].open

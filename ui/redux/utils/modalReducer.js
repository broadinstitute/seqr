import { createObjectsByIdReducer } from './reducerFactories'


// actions
const UPDATE_MODAL_STATE = 'UPDATE_MODAL_STATE'

// action creators
export const openModal = modalName => dispatch =>
  dispatch({ type: UPDATE_MODAL_STATE, updatesById: { [modalName]: { open: true } } })

export const closeModal = (modalName, confirmed) => (dispatch, getState) => {
  if (getState().modal[modalName].confirmOnClose && !confirmed) {
    dispatch({ type: UPDATE_MODAL_STATE, updatesById: { [modalName]: { confirming: true } } })
  } else {
    dispatch({ type: UPDATE_MODAL_STATE, updatesById: { [modalName]: { open: false, confirming: false, confirmOnClose: null } } })
  }
}

export const cancelCloseModal = modalName => dispatch =>
  dispatch({ type: UPDATE_MODAL_STATE, updatesById: { [modalName]: { confirming: false } } })

export const setModalConfirm = (modalName, confirmMessage) => dispatch =>
  dispatch({ type: UPDATE_MODAL_STATE, updatesById: { [modalName]: { confirmOnClose: confirmMessage } } })

// root reducer
export default {
  modal: createObjectsByIdReducer(UPDATE_MODAL_STATE),
}

// basic selectors
export const getModalOpen = (state, modalName) => state.modal[modalName] && state.modal[modalName].open
export const getModalConfim = (state, modalName) => state.modal[modalName] && (state.modal[modalName].confirming || null) && state.modal[modalName].confirmOnClose
export const getOpenModals = state => Object.keys(state.modal).filter(modalName => state.modal[modalName].open)

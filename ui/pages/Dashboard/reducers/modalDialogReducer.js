const defaultState = {
  modalIsVisible: false,
  modalType: null,
  modalProjectGuid: null,
}

// actions
const SHOW_MODAL = 'SHOW_MODAL'
const HIDE_MODAL = 'HIDE_MODAL'

// action creators
export const showModal = (modalType, modalProjectGuid) => ({
  type: SHOW_MODAL,
  newState: { modalIsVisible: true, modalType, modalProjectGuid },
})

export const hideModal = () => ({
  type: HIDE_MODAL,
  newState: defaultState,
})


// reducer
const modalDialogReducer = (modalState = defaultState, action) => {
  switch (action.type) {
    case HIDE_MODAL:
    case SHOW_MODAL:
      return { ...modalState, ...action.newState }
    default:
      return modalState
  }
}

export default modalDialogReducer

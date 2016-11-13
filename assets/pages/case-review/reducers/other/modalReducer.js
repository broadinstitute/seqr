
// actions
const SHOW_MODAL = "show_modal"


// action creators
export const showModal = (modalId) => ({type: SHOW_MODAL, id: modalId})
export const hideModal = () => ({type: SHOW_MODAL, id: null})

// selectors
export const getModalId = (modalState) => modalState[SHOW_MODAL]


// reducer
const modalReducer = (state = {SHOW_MODAL: null}, action) => {
    switch(action.type) {
        case SHOW_MODAL:
            return { ...state, SHOW_MODAL: action.id }
        default:
            return state
    }
}

export default modalReducer;





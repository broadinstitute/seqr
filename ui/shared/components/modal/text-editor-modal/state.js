import { createObjectsByIdReducer } from 'shared/utils/reducerUtils'

export const DEFAULT_TEXT_EDITOR_MODAL_ID = 'default'

// actions
const UPDATE_TEXT_EDITOR_MODAL = 'UPDATE_TEXT_EDITOR_MODAL'

// action creators
export const initTextEditorModal = (
  modalId = DEFAULT_TEXT_EDITOR_MODAL_ID,
) => ({
  type: UPDATE_TEXT_EDITOR_MODAL,
  updatesById: {
    [modalId]: {
      isVisible: false,
      allowRichText: false,
      title: '',
      initialText: '',
      formSubmitUrl: '/',
    },
  },
})


export const showTextEditorModal = (
  formSubmitUrl = '',
  title = '',
  initialText = '',
  allowRichText = false,
  modalId = DEFAULT_TEXT_EDITOR_MODAL_ID,
) => ({
  type: UPDATE_TEXT_EDITOR_MODAL,
  updatesById: {
    [modalId]: {
      isVisible: true,
      allowRichText,
      title,
      initialText,
      formSubmitUrl,
    },
  },
})


export const hideTextEditorModal = (modalId = DEFAULT_TEXT_EDITOR_MODAL_ID) => ({
  type: UPDATE_TEXT_EDITOR_MODAL,
  updatesById: {
    [modalId]: { isVisible: false },
  },
})

// selectors
export const getTextEditorModals = state => state.textEditorModals

export const textEditorModalState = {
  textEditorModals: createObjectsByIdReducer(UPDATE_TEXT_EDITOR_MODAL, {}, false),
}

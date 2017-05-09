import { createSingleObjectReducer } from 'shared/utils/reducerUtils'

// actions
const UPDATE_RICH_TEXT_EDITOR_MODAL = 'UPDATE_RICH_TEXT_EDITOR_MODAL'

// action creators
export const showRichTextEditorModal = (title, initialText, formSubmitUrl) => ({ type: UPDATE_RICH_TEXT_EDITOR_MODAL,
  updates: { isVisible: true, title, initialText, formSubmitUrl },
})
export const hideRichTextEditorModal = () => ({ type: UPDATE_RICH_TEXT_EDITOR_MODAL, updates: { isVisible: false } })

// selectors
export const getRichTextEditorModalIsVisible = state => state.richTextEditorModal.isVisible
export const getRichTextEditorModalTitle = state => state.richTextEditorModal.title
export const getRichTextEditorModalInitialText = state => state.richTextEditorModal.initialText
export const getRichTextEditorModalSubmitUrl = state => state.richTextEditorModal.formSubmitUrl

// state
const defaultState = {
  isVisible: false,
  title: null,
  initialText: null,
  formSubmitUrl: null,
}

export const richTextEditorModalState = {
  richTextEditorModal: createSingleObjectReducer(UPDATE_RICH_TEXT_EDITOR_MODAL, defaultState, true),
}

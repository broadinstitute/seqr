import { createSingleObjectReducer } from 'redux/utils/reducerUtils'

// actions
const UPDATE_PEDIGREE_IMAGE_ZOOM_MODAL = 'UPDATE_PEDIGREE_IMAGE_ZOOM_MODAL'

// action creators - pedigreeZoomModal
export const showPedigreeImageZoomModal = family => ({ type: UPDATE_PEDIGREE_IMAGE_ZOOM_MODAL, updates: { isVisible: true, family } })
export const hidePedigreeImageZoomModal = () => ({ type: UPDATE_PEDIGREE_IMAGE_ZOOM_MODAL, updates: { isVisible: false } })

//selectors
export const getPedigreeImageZoomModalIsVisible = state => state.pedigreeImageZoomModal.isVisible
export const getPedigreeImageZoomModalFamily = state => state.pedigreeImageZoomModal.family


const defaultState = {
  isVisible: false,
  family: null,
}

export const pedigreeImageZoomModalState = {
  pedigreeImageZoomModal: createSingleObjectReducer(UPDATE_PEDIGREE_IMAGE_ZOOM_MODAL, defaultState, false),
}

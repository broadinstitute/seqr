import modalReducer from './other/modalReducer'

import { combineReducers } from 'redux'


// other reducer
const otherReducer = combineReducers({
    'edit_internal_notes_modal': modalReducer,
    'edit_internal_summary_modal': modalReducer,
    'zoomed_in_pedigree_modal': modalReducer,

    'phenotipds_pdf_modal': modalReducer,
})


export default otherReducer;


// selectors
export const getEditInternalNotesModalState = (state) => state.other.edit_internal_notes_modal
export const getEditInternalSummaryModalState = (state) => state.other.edit_internal_summary_modal
export const getZoomedInPedigreeModalState = (state) => state.other.zoomed_in_pedigree_modal
export const getGetPhenotipdsPdfModalState = (state) => state.other.phenotipds_pdf_modal

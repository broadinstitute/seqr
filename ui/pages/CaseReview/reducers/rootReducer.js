import { combineReducers } from 'redux'
import { zeroActionsReducer, createSingleObjectReducer, createObjectsByIdReducer } from '../../../shared/utils/reducerUtils'
import { SHOW_ALL, SORT_BY_FAMILY_NAME } from '../constants'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux

// actions
const UPDATE_INDIVIDUALS_BY_GUID = 'UPDATE_INDIVIDUALS_BY_GUID'
const UPDATE_FAMILIES_BY_GUID = 'UPDATE_FAMILIES_BY_GUID'
const UPDATE_CASE_REVIEW_TABLE_STATE = 'UPDATE_CASE_REVIEW_TABLE_STATE'
const UPDATE_PEDIGREE_ZOOM_MODAL = 'UPDATE_PEDIGREE_ZOOM_MODAL'
const UPDATE_VIEW_PHENOTIPS_MODAL = 'UPDATE_VIEW_PHENOTIPS_MODAL'
const UPDATE_EDIT_FAMILY_INFO_MODAL = 'UPDATE_EDIT_FAMILY_INFO_MODAL'

// action creators - individuals and families
export const updateIndividualsByGuid = individualsByGuid => ({ type: UPDATE_INDIVIDUALS_BY_GUID, updatesById: individualsByGuid })
export const updateFamiliesByGuid = familiesByGuid => ({ type: UPDATE_FAMILIES_BY_GUID, updatesById: familiesByGuid })

// action creators - caseReviewTableState
export const updateFamiliesFilter = familiesFilter => ({ type: UPDATE_CASE_REVIEW_TABLE_STATE, updates: { familiesFilter } })
export const updateFamiliesSortOrder = familiesSortOrder => ({ type: UPDATE_CASE_REVIEW_TABLE_STATE, updates: { familiesSortOrder } })
export const updateFamiliesSortDirection = familiesSortDirection => ({ type: UPDATE_CASE_REVIEW_TABLE_STATE, updates: { familiesSortDirection } })
export const updateShowDetails = showDetails => ({ type: UPDATE_CASE_REVIEW_TABLE_STATE, updates: { showDetails } })

// action creators - pedigreeZoomModal
export const showPedigreeZoomModal = family => ({ type: UPDATE_PEDIGREE_ZOOM_MODAL, updates: { isVisible: true, family } })
export const hidePedigreeZoomModal = () => ({ type: UPDATE_PEDIGREE_ZOOM_MODAL, updates: { isVisible: false } })

export const showViewPhenotipsModal = (project, individual) => ({ type: UPDATE_VIEW_PHENOTIPS_MODAL, updates: { isVisible: true, project, individual } })
export const hideViewPhenotipsModal = () => ({ type: UPDATE_VIEW_PHENOTIPS_MODAL, updates: { isVisible: false } })

export const showEditFamilyInfoModal = (title, initialText, formSubmitUrl) => ({ type: UPDATE_EDIT_FAMILY_INFO_MODAL,
  updates: { isVisible: true, title, initialText, formSubmitUrl },
})
export const hideEditFamilyInfoModal = () => ({ type: UPDATE_EDIT_FAMILY_INFO_MODAL, updates: { isVisible: false } })


const rootReducer = combineReducers({
  familiesByGuid: createObjectsByIdReducer(UPDATE_FAMILIES_BY_GUID),
  individualsByGuid: createObjectsByIdReducer(UPDATE_INDIVIDUALS_BY_GUID),
  familyGuidToIndivGuids: zeroActionsReducer,
  project: zeroActionsReducer,
  user: zeroActionsReducer,
  caseReviewTableState: createSingleObjectReducer(UPDATE_CASE_REVIEW_TABLE_STATE, {
    familiesFilter: SHOW_ALL,
    familiesSortOrder: SORT_BY_FAMILY_NAME,
    familiesSortDirection: 1,
    showDetails: true,
  }, true),
  pedigreeZoomModal: createSingleObjectReducer(UPDATE_PEDIGREE_ZOOM_MODAL, {
    isVisible: false,
    family: null,
  }, true),
  editFamilyInfoModal: createSingleObjectReducer(UPDATE_EDIT_FAMILY_INFO_MODAL, {
    isVisible: false,
    title: null,
    initialText: null,
    formSubmitUrl: null,
  }, true),
  viewPhenoTipsModal: createSingleObjectReducer(UPDATE_VIEW_PHENOTIPS_MODAL, {
    isVisible: false,
    project: null,
    individual: null,
  }, true),
})


export default rootReducer


// basic selectors
export const getFamiliesByGuid = state => state.familiesByGuid
export const getIndividualsByGuid = state => state.individualsByGuid
export const getFamilyGuidToIndivGuids = state => state.familyGuidToIndivGuids
export const getProject = state => state.project
export const getUser = state => state.user
export const getCaseReviewTableState = state => state.caseReviewTableState

export const getFamiliesFilter = state => state.caseReviewTableState.familiesFilter
export const getFamiliesSortOrder = state => state.caseReviewTableState.familiesSortOrder
export const getFamiliesSortDirection = state => state.caseReviewTableState.familiesSortDirection
export const getShowDetails = state => state.caseReviewTableState.showDetails

export const getPedigreeZoomModalIsVisible = state => state.pedigreeZoomModal.isVisible
export const getPedigreeZoomModalFamily = state => state.pedigreeZoomModal.family

export const getEditFamilyInfoModalIsVisible = state => state.editFamilyInfoModal.isVisible
export const getEditFamilyInfoModalTitle = state => state.editFamilyInfoModal.title
export const getEditFamilyInfoModaInitialText = state => state.editFamilyInfoModal.initialText
export const getEditFamilyInfoModalSubmitUrl = state => state.editFamilyInfoModal.formSubmitUrl

export const getViewPhenotipsModalIsVisible = state => state.viewPhenoTipsModal.isVisible
export const getViewPhenotipsModalProject = state => state.viewPhenoTipsModal.project
export const getViewPhenotipsModalIndividual = state => state.viewPhenoTipsModal.individual


/**
 * Returns the sections of state to save in local storage in the browser.
 *
 * @param state The full redux state object.
 *
 * @returns A copy of state with restoredState applied
 */
export const getStateToSave = state => state.caseReviewTableState

/**
 * Applies state to save in local storage in the browser.
 *
 * @param state The full redux state object.
 * @param restoredState Sections of state that have been restored from local storage.
 * @returns A copy of state with restoredState applied
 */
export const applyRestoredState = (state, restoredState) => {
  const result = { ...state, caseReviewTableState: restoredState }
  console.log('with restored state:\n  ', result)
  return result
}

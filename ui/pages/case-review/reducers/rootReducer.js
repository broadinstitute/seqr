import { combineReducers } from 'redux'


// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux

// actions
const UPDATE_CASE_REVIEW_STATUSES = 'UPDATE_CASE_REVIEW_STATUSES'
const UPDATE_INTERNAL_CASE_REVIEW_NOTES = 'UPDATE_INTERNAL_CASE_REVIEW_NOTES'
const UPDATE_INTERNAL_CASE_REVIEW_SUMMARY = 'UPDATE_INTERNAL_CASE_REVIEW_SUMMARY'
//const TOGGLE_SHOW_DETAILS = 'TOGGLE_SHOW_DETAILS'

// action creators
export const updateCaseReviewStatuses = individualGuidToCaseReviewStatus => ({
  type: UPDATE_CASE_REVIEW_STATUSES,
  individualGuidToCaseReviewStatus,
})

export const updateInternalCaseReviewNotes = (familyGuid, notes) => ({
  type: UPDATE_INTERNAL_CASE_REVIEW_NOTES,
  familyGuid,
  notes,
})

export const updateInternalCaseReviewSummary = (familyGuid, summary) => ({
  type: UPDATE_INTERNAL_CASE_REVIEW_SUMMARY,
  familyGuid,
  summary,
})

// reducer
const noopReducer = (state = {}) => {
  return state
}

const userReducer = noopReducer
const projectReducer = noopReducer
const familyGuidToIndivGuidsReducer = noopReducer

const individualsByGuidReducer = (individualsByGuid = {}, action) => {
  switch (action.type) {
    case UPDATE_CASE_REVIEW_STATUSES: {
      const updatedIndividualsByGuid = Object.keys(action.individualGuidToCaseReviewStatus).reduce(
        (acc, guid) => ({
          ...acc,
          [guid]: { ...individualsByGuid[guid], caseReviewStatus: action.individualGuidToCaseReviewStatus[guid] },
        }),
        {})

      return {
        ...individualsByGuid,
        ...updatedIndividualsByGuid,
      }
    }
    default:
      return individualsByGuid
  }
}

const familiesByGuidReducer = (familiesByGuid = {}, action) => {
  switch (action.type) {
    case UPDATE_INTERNAL_CASE_REVIEW_NOTES: {
      const copy = { ...familiesByGuid }
      copy[action.familyGuid].internalCaseReviewNotes = action.notes
      return copy
    }
    case UPDATE_INTERNAL_CASE_REVIEW_SUMMARY: {
      const copy = { ...familiesByGuid }
      copy[action.familyGuid].internalCaseReviewSummary = action.summary
      return copy
    }
    default:
      return familiesByGuid
  }
}

const rootReducer = combineReducers({
  user: userReducer,
  project: projectReducer,
  familiesByGuid: familiesByGuidReducer,
  individualsByGuid: individualsByGuidReducer,
  familyGuidToIndivGuids: familyGuidToIndivGuidsReducer,
})

export default rootReducer

// selectors
//export const getUser = (state) => state.stored.user

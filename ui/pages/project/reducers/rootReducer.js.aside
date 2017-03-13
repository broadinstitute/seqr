import { combineReducers } from 'redux'


// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux

// actions
const UPDATE_INDIVIDUALS_BY_GUID = 'UPDATE_INDIVIDUALS_BY_GUID'
const UPDATE_FAMILIES_BY_GUID = 'UPDATE_FAMILIES_BY_GUID'

// action creators
export const updateIndividualsByGuid = individualsByGuid => ({
  type: UPDATE_INDIVIDUALS_BY_GUID,
  individualsByGuid,
})

export const updateFamiliesByGuid = familiesByGuid => ({
  type: UPDATE_FAMILIES_BY_GUID,
  familiesByGuid,
})


// reducers
const individualsByGuidReducer = (individualsByGuid = {}, action) => {
  switch (action.type) {
    case UPDATE_INDIVIDUALS_BY_GUID:
      return { ...individualsByGuid, ...action.individualsByGuid }
    default:
      return individualsByGuid
  }
}

const familiesByGuidReducer = (familiesByGuid = {}, action) => {
  switch (action.type) {
    case UPDATE_FAMILIES_BY_GUID: {
      return { ...familiesByGuid, ...action.familiesByGuid }
    }
    default:
      return familiesByGuid
  }
}

const zeroActionsReducer = (state = {}) => {
  return state
}

const userReducer = zeroActionsReducer
const projectReducer = zeroActionsReducer
const familyGuidToIndivGuidsReducer = zeroActionsReducer

const rootReducer = combineReducers({
  familiesByGuid: familiesByGuidReducer,
  individualsByGuid: individualsByGuidReducer,
  familyGuidToIndivGuids: familyGuidToIndivGuidsReducer,
  user: userReducer,
  project: projectReducer,
})

export default rootReducer

// selectors
//export const getUser = (state) => state.stored.user

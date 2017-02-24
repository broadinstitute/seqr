import { combineReducers } from 'redux'
import { zeroActionsReducer, createObjectsByIdReducer } from '../../../shared/utils/reducerUtils'

// action creators and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux

// actions
const UPDATE_INDIVIDUALS_BY_GUID = 'UPDATE_INDIVIDUALS_BY_GUID'
const UPDATE_FAMILIES_BY_GUID = 'UPDATE_FAMILIES_BY_GUID'

// action creators
export const updateIndividualsByGuid = individualsByGuid => ({ type: UPDATE_INDIVIDUALS_BY_GUID,
  updatesById: individualsByGuid,
})

export const updateFamiliesByGuid = familiesByGuid => ({ type: UPDATE_FAMILIES_BY_GUID,
  updatesById: familiesByGuid,
})

const rootReducer = combineReducers({
  familiesByGuid: createObjectsByIdReducer(UPDATE_FAMILIES_BY_GUID),
  individualsByGuid: createObjectsByIdReducer(UPDATE_INDIVIDUALS_BY_GUID),
  familyGuidToIndivGuids: zeroActionsReducer,
  user: zeroActionsReducer,
  project: zeroActionsReducer,
})

export default rootReducer

// selectors
//export const getUser = (state) => state.stored.user

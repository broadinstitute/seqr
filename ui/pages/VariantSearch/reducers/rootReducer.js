import { combineReducers } from 'redux'
//import { SHOW_ALL, SORT_BY_PROJECT_NAME } from '../constants'
import { zeroActionsReducer, createObjectsByIdReducer } from 'redux/utils/reducerFactories'
import {
  immutableUserState,
  immutableProjectState,
  familyState,
  familiesByGuidState,
} from 'redux/utils/commonDataActionsAndSelectors'


/**
 * Action creator and reducers in one file as suggested by https://github.com/erikras/ducks-modular-redux
 */
export const UPDATE_VARIANTS = 'UPDATE_VARIANTS'

export const updateVariants = variantsById => ({ type: UPDATE_VARIANTS, updatesById: variantsById })


const rootReducer = combineReducers({
  ...immutableUserState,
  ...immutableProjectState,
  ...familyState,
  ...familiesByGuidState,
  variants: createObjectsByIdReducer(UPDATE_VARIANTS),
  searchParams: zeroActionsReducer,
})

export default rootReducer

// selectors
//export const getUser = (state) => state.stored.user


/**
 * Returns the sections of state to save in local storage in the browser.
 *
 * @param state The full redux state object.
 *
 * @returns A copy of state with restoredState applied
 */
export const getStateToSave = state => state.searchParams

/**
 * Applies state to save in local storage in the browser.
 *
 * @param state The full redux state object.
 * @param restoredState Sections of state that have been restored from local storage.
 * @returns A copy of state with restoredState applied
 */
export const applyRestoredState = (state, restoredState) => {
  const result = { ...state, searchParams: restoredState }
  console.log('with restored state:\n  ', result)
  return result
}

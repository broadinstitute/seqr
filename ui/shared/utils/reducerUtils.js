
/**
 * Reducer for parts of the state tree that don't change after they are initialized
 *
 * @param state
 */
export const zeroActionsReducer = (state = {}) => {
  return state
}

/**
 * Returns a reducer function which can process a single action whose action id = the updateStateActionId
 * Besides the 'type' attribute, the action objects processed by this reducer are also epxected to have a
 * 'updatedState' attribute. Any fields in the updatedState object will be copied into the state.
 *
 * @param updateStateActionId
 */
export const createUpdateStateReducer = (updateStateActionId, defaultState = {}) => {
  const updateStateReducer = (state = defaultState, action) => {
    switch (action.type) {
      case updateStateActionId:
        //console.log('UpdateStateReducer', action, state, { ...state, ...action.updatedState })
        return { ...state, ...action.updatedState }
      default:
        return state
    }
  }

  return updateStateReducer
}

/**
 * Returns a reducer function which manages a state object consisting of
 *   { key1 : obj1, key2 : obj2 ... } pairs.
 *
 * It supports a single action whose action id = the updateStateActionId.
 *
 * @param updateStateActionId
 */
/* eslint-disable array-callback-return */
export const createUpdateObjectByKeyReducer = (updateStateActionId, defaultState = {}) => {
  const updatableStateReducer = (state = defaultState, action) => {
    switch (action.type) {
      case updateStateActionId: {
        const copyOfState = { ...state }
        Object.entries(action.updatedState).map(([key, obj]) => {
          if (obj === 'DELETE') {
            delete copyOfState[key]
          } else {
            copyOfState[key] = { ...copyOfState[key], ...obj }
          }
        })
        return copyOfState
      }
      default:
        return state
    }
  }

  return updatableStateReducer
}

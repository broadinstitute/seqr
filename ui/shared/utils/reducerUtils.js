/**
 * Redux reducers take a 'state' object representing the current application
 * state, and an 'action' object specifying some change to that state.
 * They apply the change and return the updated 'state' object.
 * For more details, see: http://redux.js.org/docs/basics/Reducers.html
 *
 * This module provides generic reducers that can be used to manage the following common types of
 * state shapes:
 *
 * { ... } - zero actions - arbitrary state shape that doesn't change after it's initialized, so
 *          this reducer doesn't perform any actions.
 *
 * value - single value - reducer supports 1 action that replaces the value with a new value.
 *
 * { key1: value1, key2: value2 .. } - single object - reducer supports 1 action that allows
 *          changing the values of one or more keys.
 *
 * { id1: { key1: value1, key2: value2, .. },
 *   id2: { key1: value1, key2: value2, .. },
 *   id3: ... }  -  objects by id - reducer supports several actions:
 *          adding or deleting objects by id, and updating the values within one or more objects
 *          specified by id.
 *
 *
 * ==========
 * Additional state shapes that may be implemnted as needed:
 *
 * { id1: value1, id2: value2 .. } - values by id - reducer supports several actions:
 *          adding or deleting values by id, and replacing one or more values by id.
 *
 * [ value1, value2, .. ] - single array - supports actions that add and remove values from the array
 *
 * { id1: [ value1, value2, .. ]
 *   id2: [ value1, value2, .. ] - arrays by id
 */

/**
 * Reducer that can be used to manage any state that doesn't change after it's initialized.
 */
export const zeroActionsReducer = (state = {}) => {
  return state
}

/**
 * Factory function that creates a reducer for managing any state object that's treated as a single
 * atomic value, where the only supported modification is to replace this value with a new value.
 *
 * As an example use case, lets say an app has one or more on/off toggles. Each of these toggles is
 * bound to a single state variable: 'isOn' which is either true or false.
 *
 * This function can be used to create the reducer(s) for managing a toggle's state:
 *
 * const rootReducer = combineReducers({
 *        toggleA: createSingleValueReducer('UPDATE_TOGGLE_A'),
 *        toggleB: createSingleValueReducer('UPDATE_TOGGLE_B'),
 *        ...
 *      })
 *
 * Here, the argument 'UPDATE_TOGGLE_A' specifies the action type that will later be dispatched
 * to update that toggle's state. For example, to set a toggle to "off":
 *
 * dispatch({
 *      type: 'UPDATE_TOGGLE_A',
 *      newValue: false,
 * })
 *
 * @param updateActionType (string) action.type that will later be used to replace the state with a
 * new state.
 */
export const createSingleValueReducer = (updateActionType, initialState = {}, debug = false) => {
  const reducer = (state = initialState, action) => {
    if (!action) {
      return state
    }

    switch (action.type) {
      case updateActionType: {
        if (action.newValue === undefined) {
          console.error(`Invalid ${updateActionType} action: ${JSON.stringify(action)}. action.newValue is undefined.`)
          return state
        }
        if (debug) {
          console.log(`singleValueReducer: applying ${JSON.stringify(action)} action. State changing from ${JSON.stringify(state)} to ${action.newValue}`)
        }
        return action.newValue
      }
      default:
        return state
    }
  }

  return reducer
}


/**
 * Factory function that creates a reducer for managing a state object with some fixed set of keys.
 * The reducer supports an 'UPDATE' action that can be used to set one or more
 * of these keys to new values.
 *
 * As an example use case, lets say an app displays several instances of a widget whose state
 * consists of this state object:
 *
 *    { isVisible: true, size: 5, names:  ['bob', 'gary', .. ], ... }
 *
 * This function can be used to create a reducer for this state:
 *
 *    const widgetReducer = createSingleObjectReducer('UPDATE_WIDGET')
 *
 * Here, the argument 'UPDATE_WIDGET' specifies the action type that will later be dispatched to
 * update the widget's state.
 *
 * After this, an action with type 'UPDATE_WIDGET' can be dispatched:
 *
 *    dispatch({
 *      type: 'UPDATE_WIDGET',
 *      updates: { isVisible: false, names: ['jim', 'liza'] }
 *    })
 *
 * which will cause the state object to be updated to:
 *
 *    { isVisible: false, size: 5, names:  ['jim', 'liza'], ... }
 *
 * These reducers can also be used with combineReducers(..):
 *
 *    const rootReducer = combineReducers({
 *        widget1: createSingleObjectReducer('UPDATE_WIDGET1'),
 *        widget2: createSingleObjectReducer('UPDATE_WIDGET2'),
 *        other: ..,
 *        ..
 *    })
 *
 * @param updateActionType (string) action.type that will later be used to update the state object.
 */
export const createSingleObjectReducer = (updateActionType, initialState = {}, debug = false) => {
  const reducer = (state = initialState, action) => {
    if (!action) {
      return state
    }

    switch (action.type) {
      case updateActionType: {
        if (action.updates === undefined) {
          console.error(`Invalid ${updateActionType} action: ${JSON.stringify(action)}. action.updates is undefined.`)
          return state
        }

        const newState = { ...state, ...action.updates }
        if (debug) {
          console.log(`singleObjectReducer: applying ${JSON.stringify(action)} action. State changing from ${JSON.stringify(state)} to ${JSON.stringify(newState)}`)
        }
        return newState
      }
      default:
        return state
    }
  }

  return reducer
}

/**
 * Factory function that creates a reducer for managing a state object that looks like:
 *
 * { id1: { key1: valueA, key2: valueB, key3: valueC },
 *   id2: { key1: valueI, key2: valueJ, key3: valueK },
 *   id3: ...
 * }
 *
 * This state object is analogous to a database table, where the contained objects represent table
 * rows and have identical sets of keys but different values, so that each key can be thought of as
 * a column in the table.
 *
 * This reducer supports a single action type that can be used to transform the underlying state
 * in several ways:
 *    - adding new objects by id
 *    - deleting objects by id
 *    - updating the values within one or more existing objects by id
 *
 * As an example, the reducer can be created as follows:
 *
 *      const tableRowReducer = createObjectsByIdReducer('UPDATE_TABLE_X')
 *
 * Here, the 'UPDATE_TABLE_X' argument specifies the action type that will later be dispatched
 * to perform modifications. For example, the action below will change some of the values and also
 * both delete some ids and add some new ids:
 *
 * dispatch({
 *   type: 'UPDATE_TABLE_X',
 *   updatesById: {
 *     id1: { key2: valueM },                                 // update key2 value in object with id1
 *     idNew: { key1: valueX, key2: valueY, key3: valueZ },   // add new object and id
 *     id2: null,                                             // delete id2
 *   }
 *  })
 *
 * The resulting state after this action would look like:
 *
 * { id1: { key1: valueA, key2: valueM, key3: valueC },
 *   idNew: { key1: valueX, key2: valueY, key3: valueZ },
 *   id3: ...
 * }
 *
 * @param updateStateActionId (string) action.type that will later be used to update the state object.
 */
/* eslint-disable array-callback-return */
export const createObjectsByIdReducer = (updateActionType, initialState = {}, debug = false) => {
  const reducer = (state = initialState, action) => {
    if (!action) {
      return state
    }

    switch (action.type) {
      case updateActionType: {
        if (action.updatesById === undefined) {
          console.error(`Invalid ${updateActionType} action: ${JSON.stringify(action)}. action.updatesById is undefined.`)
          return state
        }

        const shallowCopy = { ...state }
        Object.entries(action.updatesById).map(([id, obj]) => {
          if (obj == null) {
            // if the id is mapped to a null or undefined value, then delete this id
            delete shallowCopy[id]
          } else {
            // look up the object by id and apply the same update operation as in the
            // singleObjectReducer above. This also works to add new ids.
            shallowCopy[id] = { ...shallowCopy[id], ...obj }
          }
        })
        if (debug) {
          console.log(`objectsByIdReducer: applying ${JSON.stringify(action)} action.`)
        }
        return shallowCopy
      }
      default:
        return state
    }
  }

  return reducer
}

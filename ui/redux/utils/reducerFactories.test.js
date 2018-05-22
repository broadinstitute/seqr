/* eslint-disable no-undef */
/* eslint-disable object-property-newline */

/**
 * Reference:
 * http://facebook.github.io/jest/docs/expect.html
 * https://github.com/facebookincubator/create-react-app/blob/master/packages/react-scripts/template/README.md#running-tests
 */
import { zeroActionsReducer, createSingleValueReducer, createSingleObjectReducer, createObjectsByIdReducer } from './reducerFactories'


describe('reducerUtils tests', () => {

  /****************************/
  /** Test zeroActionsReducer */
  /****************************/
  test('zeroActionReducer', () => {
    const state = { test: 1 }
    expect(zeroActionsReducer(state)).toEqual(state)

    expect(zeroActionsReducer(state, 'SOME_ACTION')).toEqual(state)
  })


  /****************************/
  /** Test singleValueReducer */
  /****************************/

  test('createSingleValueReducer test initialization', () => {
    const singleValueReducerWithInitialState = createSingleValueReducer('TEST_ACTION', { test: 1 })
    expect(singleValueReducerWithInitialState()).toEqual({ test: 1 })

    const singleValueReducerWithoutInitialState = createSingleValueReducer('TEST_ACTION')
    expect(singleValueReducerWithoutInitialState()).toEqual({})
  })

  test('createSingleValueReducer test update action', () => {
    const initialState = 'someValue'
    const singleValueReducer = createSingleValueReducer('UPDATE_TEST_ACTION', initialState)

    // test undefined or invalid actions
    expect(singleValueReducer()).toEqual(initialState)
    expect(singleValueReducer(initialState)).toEqual(initialState)
    expect(singleValueReducer(initialState, { type: 'UNKNOWN_ACTION' })).toEqual(initialState)
    expect(singleValueReducer(initialState, { type: 'UPDATE_TEST_ACTION', wrongKeyName: 'anotherValue' })).toEqual(initialState)

    // test valid action
    expect(singleValueReducer('someValue', { type: 'UPDATE_TEST_ACTION', newValue: 'anotherValue' })).toEqual('anotherValue')
    expect(singleValueReducer(1, { type: 'UPDATE_TEST_ACTION', newValue: 2 })).toEqual(2)
    expect(singleValueReducer([1, 2, 3], { type: 'UPDATE_TEST_ACTION', newValue: [5, 6, 7] })).toEqual([5, 6, 7])
    expect(singleValueReducer({ someKey: 1 }, { type: 'UPDATE_TEST_ACTION', newValue: { anotherKey: 2 } })).toEqual({ anotherKey: 2 })
    expect(singleValueReducer({ someKey: 1 }, { type: 'UPDATE_TEST_ACTION', newValue: 'x' })).toEqual('x')
  })


  /****************************/
  /** Test singleObjectReducer */
  /****************************/
  test('createSingleObjectReducer test initialization', () => {
    const singleObjectReducerWithInitialState = createSingleObjectReducer('TEST_ACTION', { test: 1 })
    expect(singleObjectReducerWithInitialState()).toEqual({ test: 1 })

    const singleObjectReducerWithoutInitialState = createSingleObjectReducer('TEST_ACTION')
    expect(singleObjectReducerWithoutInitialState()).toEqual({})
  })


  test('createSingleObjectReducer test update action', () => {
    const initialState = { key1: 1, key2: 1, key3: 1 }
    const singleObjectReducer = createSingleObjectReducer('UPDATE_TEST_ACTION', initialState)

    // test undefined or invalid actions
    expect(singleObjectReducer()).toEqual(initialState)
    expect(singleObjectReducer(initialState)).toEqual(initialState)
    expect(singleObjectReducer(initialState, { type: 'UNKNOWN_ACTION' })).toEqual(initialState)
    expect(singleObjectReducer(initialState, { type: 'UPDATE_TEST_ACTION', wrongKeyName: { someKey: 3 } })).toEqual(initialState)

    // test valid action results
    const action = { type: 'UPDATE_TEST_ACTION', updates: { key2: 2, key3: 3, newKey: 4 } }
    expect(singleObjectReducer(undefined, action)).toEqual({ key1: 1, key2: 2, key3: 3, newKey: 4 })
  })


  /****************************/
  /** Test objectsByIdReducer */
  /****************************/


  test('createObjectsByIdReducer test initialization', () => {
    const objectsByIdReducerWithInitialState = createObjectsByIdReducer('TEST_ACTION', null, { i1: { test: 1 } })
    expect(objectsByIdReducerWithInitialState()).toEqual({ i1: { test: 1 } })

    const objectsByIdReducerWithoutInitialState = createObjectsByIdReducer('TEST_ACTION')
    expect(objectsByIdReducerWithoutInitialState()).toEqual({})
  })


  test('createObjectsByIdReducer test update action', () => {
    const initialState = {
      id1: { key1: 1, key2: 1 },
      id2: { key1: 3, key2: 4 },
    }

    const objectsByIdReducer = createObjectsByIdReducer('UPDATE_TEST_ACTION', null, initialState)

    // test #1 - undefined or invalid actions
    expect(objectsByIdReducer()).toEqual(initialState)
    expect(objectsByIdReducer(initialState)).toEqual(initialState)
    expect(objectsByIdReducer(initialState, { type: 'UNKNOWN_ACTION' })).toEqual(initialState)
    expect(objectsByIdReducer(initialState, { type: 'UPDATE_TEST_ACTION', wrongKeyName: { someKey: 3 } })).toEqual(initialState)

    // test #2 - valid update action
    let action = null
    action = { type: 'UPDATE_TEST_ACTION', updatesById: {
      id1: { key1: 2, key2: 3, newKey: 4 },
    } }
    expect(objectsByIdReducer(undefined, action)).toEqual({
      id1: { key1: 2, key2: 3, newKey: 4 },
      id2: { key1: 3, key2: 4 },
    })

    // test #3 - valid update action with "delete id", and "add new id" operations
    action = { type: 'UPDATE_TEST_ACTION', updatesById: {
      id1: null, // delete id1
      id2: { key2: 5, newKey: 5 }, // update values of key2, and add a new key.
      newId: { key1: 5, key2: 6 }, // add new id
    } }

    expect(objectsByIdReducer(undefined, action)).toEqual({
      id2: { key1: 3, key2: 5, newKey: 5 },
      newId: { key1: 5, key2: 6 },
    })
  })

  test('createObjectsByIdReducer test update action with key', () => {
    const key = 'parentKey'
    const initialState = {
      id1: { key1: 1, key2: 1 },
      id2: { key1: 3, key2: 4 },
    }

    const objectsByIdReducer = createObjectsByIdReducer('UPDATE_TEST_ACTION', key, initialState)

    // test #1 - undefined or invalid actions
    expect(objectsByIdReducer()).toEqual(initialState)
    expect(objectsByIdReducer(initialState)).toEqual(initialState)
    expect(objectsByIdReducer(initialState, { type: 'UNKNOWN_ACTION' })).toEqual(initialState)
    expect(objectsByIdReducer(initialState, { type: 'UPDATE_TEST_ACTION', wrongKeyName: { someKey: 3 } })).toEqual(initialState)

    // test #2 - valid update action
    const action = { type: 'UPDATE_TEST_ACTION', updatesById: {
      [key]: { id1: { key1: 2, key2: 3, newKey: 4 } },
    } }
    expect(objectsByIdReducer(undefined, action)).toEqual({
      id1: { key1: 2, key2: 3, newKey: 4 },
      id2: { key1: 3, key2: 4 },
    })
  })
})
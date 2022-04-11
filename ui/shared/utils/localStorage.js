/**
 * Uses the localStorage API to save a state object in the browser under the given label.
 * @param label {string}
 * @param state {object}
 */
export const saveState = (label, state) => {
  try {
    const serializedState = JSON.stringify(state)
    localStorage.setItem(label, serializedState)
  } catch (err) {
    console.warn(err) // eslint-disable-line no-console
    // clear existing state, as most common reason for failure is out of memory
    localStorage.removeItem(label)
  }
}

/**
 * Uses the localStorage API to restored a previously-saved state object.
 * @param label {string}
 * @param state {object}
 */
export const loadState = (label) => {
  try {
    const serializedState = localStorage.getItem(label)
    if (serializedState === null) {
      return undefined
    }
    return JSON.parse(serializedState)
  } catch (err) {
    console.warn(err) // eslint-disable-line no-console
    return undefined
  }
}

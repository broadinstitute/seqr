/**
 * Uses the localStorage API to save a state object in the browser under the given label.
 *
 * @param {string} label - The label under which to save the state.
 * @param {unknown} state - The state to be serialized and saved.
 * @returns {void}
 */
export const saveState = (label: string, state: unknown): void => {
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
 *
 * @param {string} label - The label to identify the state in local storage.
 * @returns {unknown} The parsed state, or undefined if the state cannot be loaded.
 */
export const loadState = (label: string): unknown => {
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

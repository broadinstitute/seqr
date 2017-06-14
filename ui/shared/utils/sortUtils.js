/* eslint-disable no-lonely-if */
/* eslint-disable no-else-return */

/**
 * Function that takes two objects and returns:
 *   1 if a < b or b is undefined or null
 *   0 if a === b
 *   -1 if a > b or a is undefined or null
 *
 * @param a {object}
 * @param b {object}
 * @returns {number}
 */
export const genericComparator = (a, b) => {
  if (a !== undefined && a !== null && b !== undefined && b !== null) {
    if (a < b) {
      return 1
    } else if (a > b) {
      return -1
    } else {
      return 0
    }
  } else {
    if (a !== undefined && a !== null) {
      return 1
    } else if (b !== undefined && b !== null) {
      return -1
    } else {
      return 0
    }
  }
}

/* eslint-disable no-lonely-if */
/* eslint-disable no-else-return */

/**
 * A generic comparator function for comparing two values.
 *
 * @param {unknown} a - The first value to compare.
 * @param {unknown} b - The second value to compare.
 * @returns {number}
 * - 1 if a < b or b is undefined or null
 * - 0 if a === b
 * - -1 if a > b or a is undefined or null
 */
export const genericComparator = (a: unknown, b: unknown): number => {
  if (a !== undefined && a !== null && b !== undefined && b !== null) {
    if (a < b) {
      return -1
    } else if (a > b) {
      return 1
    } else {
      return 0
    }
  } else {
    if (a !== undefined && a !== null) {
      return -1
    } else if (b !== undefined && b !== null) {
      return 1
    } else {
      return 0
    }
  }
}

/**
 * Comparator function.
 */
type ComparatorFunction = (a: Record<string, unknown>, b: Record<string, unknown>) => number

/**
 * A factory function that creates a comparator function for sorting objects.
 *
 * @param {string} field - The field by which to compare objects.
 * @returns {ComparatorFunction} A comparator function that can be used for sorting objects.
 */
export const compareObjects = (field: string): ComparatorFunction => (a, b) => {
  let valA = a[field]
  let valB = b[field]
  if (typeof valA === 'string') { valA = valA.toLowerCase() }
  if (typeof valB === 'string') { valB = valB.toLowerCase() }

  return genericComparator(valA, valB)
}

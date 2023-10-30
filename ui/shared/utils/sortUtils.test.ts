import { genericComparator } from './sortUtils'

test('genericComparator', () => {
  expect(genericComparator(1, 2)).toEqual(-1)
  expect(genericComparator(1, 1)).toEqual(0)
  expect(genericComparator(1, 0)).toEqual(1)

  expect(genericComparator(0, 0)).toEqual(0)
  expect(genericComparator(0, 1)).toEqual(-1)
  expect(genericComparator(0, -1)).toEqual(1)

  expect(genericComparator(undefined, 0)).toEqual(1)
  expect(genericComparator(0, undefined)).toEqual(-1)

  // Comparing strings
  expect(genericComparator('abc', 'xyz')).toEqual(-1)
  expect(genericComparator('xyz', 'abc')).toEqual(1)
  expect(genericComparator('abc', 'abc')).toEqual(0)
  expect(genericComparator(undefined, 'abc')).toEqual(1)
  expect(genericComparator('abc', undefined)).toEqual(-1)

  // Comparing array
  expect(genericComparator([1, 2, 3], [1, 2, 3])).toEqual(0)
  expect(genericComparator([2, 3], [1, 2, 3])).toEqual(1)
  expect(genericComparator([1, 0], [1, 2, 3])).toEqual(-1)
  expect(genericComparator(undefined, [1, 2, 3])).toEqual(1)
  expect(genericComparator([1, 0], undefined)).toEqual(-1)

  // Comparing undefined and null
  expect(genericComparator(undefined, undefined)).toEqual(0)
  expect(genericComparator(null, null)).toEqual(0)
  expect(genericComparator(undefined, null)).toEqual(0)
})

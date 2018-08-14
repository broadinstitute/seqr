/* eslint-disable no-undef */

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
})
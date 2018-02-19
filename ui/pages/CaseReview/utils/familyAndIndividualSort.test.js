/* eslint-disable no-undef */

import { getFamiliesByGuid, getIndividualsByGuid } from 'shared/utils/redux/commonDataActionsAndSelectors'
import { createFamilySortComparator, createIndividualSortComparator } from './familyAndIndividualSort'

import {
  SORT_BY_FAMILY_NAME,
  SORT_BY_DATE_ADDED,
  SORT_BY_DATE_LAST_CHANGED,
} from '../constants'

import { STATE1, STATE_WITH_2_FAMILIES } from '../fixtures'


test('createIndividualSortComparator', () => {
  const indivsByGuid = getIndividualsByGuid(STATE1)
  const comparator = createIndividualSortComparator(indivsByGuid)

  expect(comparator('I021475_na19675', 'I021475_na19675')).toBe(0)
  expect(comparator('I021476_na19678', 'I021476_na19678')).toBe(0)
  expect(comparator('I021474_na19679', 'I021474_na19679')).toBe(0)

  expect(comparator('I021475_na19675', 'I021474_na19679')).toBeLessThan(0)
  expect(comparator('I021475_na19675', 'I021476_na19678')).toBeLessThan(0)
  expect(comparator('I021476_na19678', 'I021474_na19679')).toBe(0)
})


test('createFamilySortComparator', () => {
  const famsByGuid = getFamiliesByGuid(STATE_WITH_2_FAMILIES)
  const indivsByGuid = getIndividualsByGuid(STATE_WITH_2_FAMILIES)

  const comparatorByLastChangedDesc = createFamilySortComparator(SORT_BY_DATE_LAST_CHANGED, -1, famsByGuid, indivsByGuid)

  expect(comparatorByLastChangedDesc('F011652_1', 'F011652_1')).toBe(0)
  expect(comparatorByLastChangedDesc('F011652_2', 'F011652_2')).toBe(0)
  expect(comparatorByLastChangedDesc('F011652_1', 'F011652_2')).toBe(-1)

  const comparatorByLastChangedAsc = createFamilySortComparator(SORT_BY_DATE_LAST_CHANGED, 1, famsByGuid, indivsByGuid)

  expect(comparatorByLastChangedAsc('F011652_1', 'F011652_1')).toBe(0)
  expect(comparatorByLastChangedAsc('F011652_2', 'F011652_2')).toBe(0)
  expect(comparatorByLastChangedAsc('F011652_1', 'F011652_2')).toBe(1)


  const comparatorByDateAddedAsc = createFamilySortComparator(SORT_BY_DATE_ADDED, 1, famsByGuid, indivsByGuid)

  expect(comparatorByDateAddedAsc('F011652_1', 'F011652_1')).toBe(0)
  expect(comparatorByDateAddedAsc('F011652_2', 'F011652_2')).toBe(0)
  expect(comparatorByDateAddedAsc('F011652_1', 'F011652_2')).toBe(1)


  const comparatorByFamilyNameAsc = createFamilySortComparator(SORT_BY_FAMILY_NAME, 1, famsByGuid, indivsByGuid)

  expect(comparatorByFamilyNameAsc('F011652_1', 'F011652_1')).toBe(0)
  expect(comparatorByFamilyNameAsc('F011652_2', 'F011652_2')).toBe(0)
  expect(comparatorByFamilyNameAsc('F011652_1', 'F011652_2')).toBe(-1)
})

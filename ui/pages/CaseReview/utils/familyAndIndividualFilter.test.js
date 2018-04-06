/* eslint-disable no-undef */

import {
  CASE_REVIEW_STATUS_IN_REVIEW,
  CASE_REVIEW_STATUS_ACCEPTED,
} from 'shared/constants/caseReviewConstants'
import { getIndividualsByGuid, getFamiliesByGuid } from 'redux/utils/commonDataActionsAndSelectors'
import { createFamilyFilter, createIndividualFilter } from './familyAndIndividualFilter'
import {
  SHOW_ALL,
  SHOW_ACCEPTED,
  SHOW_NOT_ACCEPTED,
  SHOW_IN_REVIEW,
  SHOW_UNCERTAIN,
  SHOW_MORE_INFO_NEEDED,
  SHOW_NOT_IN_REVIEW,
  SHOW_PENDING_RESULTS_AND_RECORDS,
  SHOW_WAITLIST,
  SHOW_WITHDREW,
  SHOW_INELIGIBLE,
  SHOW_DECLINED_TO_PARTICIPATE,
} from '../constants'

import { STATE1 } from '../fixtures'

test('createFamilyFilter', () => {
  const family1 = getFamiliesByGuid(STATE1).F011652_1

  const familiesByGuid = getFamiliesByGuid(STATE1)
  const indivsByGuid = getIndividualsByGuid(STATE1)

  const filters = [
    createFamilyFilter(SHOW_ALL, familiesByGuid, indivsByGuid),
    createFamilyFilter(SHOW_ACCEPTED, familiesByGuid, indivsByGuid),
    createFamilyFilter(SHOW_NOT_ACCEPTED, familiesByGuid, indivsByGuid),
    createFamilyFilter(SHOW_IN_REVIEW, familiesByGuid, indivsByGuid),
    createFamilyFilter(SHOW_UNCERTAIN, familiesByGuid, indivsByGuid),
    createFamilyFilter(SHOW_MORE_INFO_NEEDED, familiesByGuid, indivsByGuid),
    createFamilyFilter(SHOW_NOT_IN_REVIEW, familiesByGuid, indivsByGuid),
    createFamilyFilter(SHOW_PENDING_RESULTS_AND_RECORDS, familiesByGuid, indivsByGuid),
    createFamilyFilter(SHOW_WAITLIST, familiesByGuid, indivsByGuid),
    createFamilyFilter(SHOW_WITHDREW, familiesByGuid, indivsByGuid),
    createFamilyFilter(SHOW_INELIGIBLE, familiesByGuid, indivsByGuid),
    createFamilyFilter(SHOW_DECLINED_TO_PARTICIPATE, familiesByGuid, indivsByGuid),
  ]

  expect(filters[0](family1.familyGuid)).toBe(true)
  expect(filters[1](family1.familyGuid)).toBe(true)
  expect(filters[2](family1.familyGuid)).toBe(false)
  expect(filters[3](family1.familyGuid)).toBe(false)
  expect(filters[4](family1.familyGuid)).toBe(false)
  expect(filters[5](family1.familyGuid)).toBe(false)
})


test('createIndividualFilter', () => {
  const indivsByGuid = getIndividualsByGuid(STATE1)
  const indivFilter = createIndividualFilter(indivsByGuid, new Set([CASE_REVIEW_STATUS_IN_REVIEW, CASE_REVIEW_STATUS_ACCEPTED]))

  expect(indivFilter(indivsByGuid.I021474_na19679.individualGuid)).toBe(true)
  expect(indivFilter(indivsByGuid.I021475_na19675.individualGuid)).toBe(true)
  expect(indivFilter(indivsByGuid.I021476_na19678.individualGuid)).toBe(true)

  const indivFilter2 = createIndividualFilter(indivsByGuid, new Set([CASE_REVIEW_STATUS_IN_REVIEW]))
  expect(indivFilter2(indivsByGuid.I021474_na19679.individualGuid)).toBe(false)
  expect(indivFilter2(indivsByGuid.I021475_na19675.individualGuid)).toBe(true)
  expect(indivFilter2(indivsByGuid.I021476_na19678.individualGuid)).toBe(false)

})

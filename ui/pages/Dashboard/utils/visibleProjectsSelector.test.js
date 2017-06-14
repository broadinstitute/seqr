/* eslint-disable no-undef */

import { getVisibleProjectGuids, getVisibleProjectsInSortedOrder } from './visibleProjectsSelector'

import { STATE1 } from '../fixtures'

describe('tests', () => {

  test('getVisibleProjectGuids', () => {
    const visibleProjects = getVisibleProjectGuids(STATE1)

    expect(visibleProjects.length).toBe(2)
  })

  test('getVisibleProjectsInSortedOrder', () => {
    const visibleProjects = getVisibleProjectsInSortedOrder(STATE1)

    expect(visibleProjects.length).toBe(2)
    expect(visibleProjects[0].projectGuid).toBe('R0202_tutorial')
    expect(visibleProjects[1].projectGuid).toBe('R0237_1000_genomes_demo')
  })
})

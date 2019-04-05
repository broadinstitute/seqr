/* eslint-disable no-undef */

import { getVisibleProjects } from './visibleProjectsSelector'

import { STATE1 } from '../fixtures'

describe('tests', () => {

  test('getVisibleProjects', () => {
    const visibleProjects = getVisibleProjects(STATE1)

    expect(visibleProjects.length).toBe(2)
    expect(visibleProjects[0].projectGuid).toBe('R0202_tutorial')
    expect(visibleProjects[1].projectGuid).toBe('R0237_1000_genomes_demo')
  })
})

/* eslint-disable no-undef */

import { createProjectFilter } from './projectFilter'

import { getProjectsByGuid } from '../../../redux/selectors'
import { SHOW_ALL } from '../constants'
import { STATE1 } from '../fixtures'

describe('tests', () => {

  test('createProjectFilter', () => {
    const projectsByGuid = getProjectsByGuid(STATE1)
    const projectFilter = SHOW_ALL
    const projectsFilter = createProjectFilter(projectsByGuid, projectFilter)

    expect(projectsFilter(projectsByGuid.R0237_1000_genomes_demo)).toBe(true)
    expect(projectsFilter(projectsByGuid.R0202_tutorial)).toBe(true)
  })
})

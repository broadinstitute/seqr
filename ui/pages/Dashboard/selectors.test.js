import { getProjectsByGuid } from 'redux/selectors'

import { createProjectFilter, getVisibleProjects } from './selectors'
import { STATE1 } from './fixtures'
import { SHOW_ALL } from './constants'

describe('tests', () => {

  test('createProjectFilter', () => {
    const projectsByGuid = getProjectsByGuid(STATE1)
    const projectFilter = SHOW_ALL
    const projectsFilter = createProjectFilter(projectFilter)

    expect(projectsFilter(projectsByGuid.R0237_1000_genomes_demo)).toBe(true)
    expect(projectsFilter(projectsByGuid.R0202_tutorial)).toBe(true)
  })

  test('getVisibleProjects', () => {
    const visibleProjects = getVisibleProjects(STATE1)

    expect(visibleProjects.length).toBe(3)
    expect(visibleProjects[0].projectGuid).toBe('R0202_tutorial')
    expect(visibleProjects[0].analysisGroupGuid).toBe(undefined)
    expect(visibleProjects[1].projectGuid).toBe('R0237_1000_genomes_demo')
    expect(visibleProjects[1].analysisGroupGuid).toBe(undefined)
    expect(visibleProjects[2].projectGuid).toBe('R0001_1kg')
    expect(visibleProjects[2].analysisGroupGuid).toBe('AG0000184_test_access')
  })
})

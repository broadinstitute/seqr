import orderBy from 'lodash/orderBy'

import {
  SORT_BY_PROJECT_NAME,
  SORT_BY_DATE_CREATED,
  SORT_BY_DATE_LAST_ACCESSED,
  SORT_BY_NUM_FAMILIES,
  SORT_BY_NUM_INDIVIDUALS,
  SORT_BY_PROJECT_SAMPLES,
  SORT_BY_TAGS,
  SORT_BY_ANALYSIS,

} from '../constants'


export const computeSortedProjectGuids = (projectGuids, projectsByGuid, sampleBatchesByGuid, sortColumn, sortDirection) => {
  if (projectGuids.length === 0) {
    return projectGuids
  }

  let getSortKey = null
  switch (sortColumn) {
    case SORT_BY_PROJECT_NAME: getSortKey = guid => projectsByGuid[guid].name.toLowerCase(); break
    case SORT_BY_DATE_CREATED: getSortKey = guid => projectsByGuid[guid].createdDate; break
    case SORT_BY_DATE_LAST_ACCESSED: getSortKey = guid => projectsByGuid[guid].deprecatedLastAccessedDate; break
    case SORT_BY_NUM_FAMILIES: getSortKey = guid => projectsByGuid[guid].numFamilies; break
    case SORT_BY_NUM_INDIVIDUALS: getSortKey = guid => projectsByGuid[guid].numIndividuals; break
    case SORT_BY_PROJECT_SAMPLES: getSortKey = guid => (projectsByGuid[guid].sampleBatchGuids &&
      projectsByGuid[guid].sampleBatchGuids.map(
        d => `${sampleBatchesByGuid[d].sampleType}:${sampleBatchesByGuid[d].numSamples / 10000.0}`,  // sort by data type, then number of samples
      ).join(',')) || 'A'
      break
    case SORT_BY_TAGS: getSortKey = guid => projectsByGuid[guid].numVariantTags; break
    case SORT_BY_ANALYSIS: getSortKey = (guid) => {
      // sort by % families solved, num families solved, num variant tags, num families <= in that order
      return projectsByGuid[guid].numFamilies &&
        (
          ((10e9 * projectsByGuid[guid].analysisStatusCounts.Solved || 0) / projectsByGuid[guid].numFamilies) +
          ((10e5 * projectsByGuid[guid].analysisStatusCounts.Solved || 0) || (10e-3 * projectsByGuid[guid].numFamilies))
        )
    }; break
    default:
      console.error(`Unexpected projectsTableState.SortColumn value: ${sortColumn}`)
      getSortKey = p => p.guid
  }

  if (sortColumn === SORT_BY_DATE_CREATED || sortColumn === SORT_BY_DATE_LAST_ACCESSED) {
    sortDirection *= -1
  }
  const sortedProjectGuids = orderBy(projectGuids, [getSortKey], [sortDirection === 1 ? 'asc' : 'desc'])

  return sortedProjectGuids
}

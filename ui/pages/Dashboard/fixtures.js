/** This file contains sample state to use for tests */

/* eslint-disable comma-dangle */

export const PROJECT_GUID = 'R0237_1000_genomes_demo'
export const STATE1 = {
  projectCategoriesByGuid: {
    PC000012_cmg: {
      created_by_id: 443,
      created_date: '2017-02-09T15:30:44.432Z',
      guid: 'PC000012_cmg',
      id: 12,
      last_modified_date: '2017-02-09T15:30:44.432Z',
      name: 'CMG'
    }
  },
  projectsByGuid: {
    R0202_tutorial: {
      analysisStatusCounts: {
        I: 10
      },
      canEdit: true,
      createdDate: '2015-12-17T01:57:46Z',
      deprecatedLastAccessedDate: '2017-03-14T15:21:39.716Z',
      deprecatedProjectId: 'Bootcamp2016',
      description: '',
      name: 'Tutorial',
      numFamilies: 13,
      numIndividuals: 33,
      numVariantTags: 1,
      projectCategoryGuids: [],
      projectGuid: 'R0202_tutorial',
      sampleTypeCounts: [
        { sampleType: 'WES', numSamples: 33 },
        { sampleType: 'WGS', numSamples: 15 },
        { sampleType: 'RNA', numSamples: 0 },
      ]
    },
    R0237_1000_genomes_demo: {
      analysisStatusCounts: {
        I: 11,
        Rcpc: 1
      },
      canEdit: true,
      createdDate: '2016-05-16T05:37:08.634Z',
      deprecatedLastAccessedDate: '2017-03-15T17:07:00.766Z',
      deprecatedProjectId: '1kg',
      description: '',
      name: '1000 Genomes Demo',
      numFamilies: 12,
      numIndividuals: 16,
      numVariantTags: 5,
      projectCategoryGuids: ['PC000012_cmg'],
      projectGuid: 'R0237_1000_genomes_demo',
      sampleTypeCounts: [
        { sampleType: 'WES', numSamples: 10 },
      ]
    },
  },
  user: {
    date_joined: '2015-02-19T20:22:50.633Z',
    email: 'test@test.org',
    first_name: '',
    id: 1,
    is_active: true,
    is_staff: true,
    last_login: '2017-03-02T17:58:05.166Z',
    last_name: '',
    username: 'test'
  },
  projectsTableState: {
    filter: 'SHOW_ALL',
    sortColumn: 'SORT_BY_PROJECT_NAME',
    sortDirection: -1
  },
  modalDialogState: {
    modalProjectGuid: 'R0237_1000_genomes_demo',
  }
}

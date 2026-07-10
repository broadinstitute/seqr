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
  analysisGroupsByGuid: {
    AG0000183_test_group: {
      analysisGroupGuid: "AG0000183_test_group",
      createdDate: "2018-08-09T18:53:24.207Z",
      description: "",
      familyGuids: ["F011652_1"],
      name: "Test Group",
      projectGuid: "R0237_1000_genomes_demo",
    },
    AG0000184_test_access: {
      analysisGroupGuid: 'AG0000184_test_access',
      analysisStatusCounts: {'Q': 3},
      createdDate: '2018-08-09T18:53:24.207Z',
      description: 'A sample analysis group',
      name: 'Test Access Group 1',
      numFamilies: 3,
      numIndividuals: 5,
      numVariantTags: 3,
      projectGuid: 'R0001_1kg',
      sampleTypeCounts: {'RNA': 1, 'WES': 5},
      workspaceName: 'anvil-analysis-group',
      workspaceNamespace: 'my-seqr-billing',
    },
  },
  user: {
    date_joined: '2015-02-19T20:22:50.633Z',
    email: 'test@test.org',
    first_name: '',
    id: 1,
    is_active: true,
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

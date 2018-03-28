/**
 * This module contains actions, selectors, and reducer functions that are useful across multiple seqr pages -
 * particularly pages that show:
 *
 *  - 1 or multiple projects
 *  - 1 or multiple families,
 *  - 1 or multiple indivudals,
 *  etc.
 */

// TODO this field is deprecated, all of these should either live in the main app's rootReducer or in page-specific reducers

import { zeroActionsReducer, createSingleObjectReducer, createObjectsByIdReducer } from './reducerFactories'

// single user
export const immutableUserState = {
  user: zeroActionsReducer,
}
export const getUser = state => state.user


// single project
const UPDATE_PROJECT = 'UPDATE_PROJECT'
export const immutableProjectState = {
  project: zeroActionsReducer,
}
export const projectState = {
  project: createSingleObjectReducer(UPDATE_PROJECT, {}, true),
}
export const getProject = state => state.project
export const updateProject = project => ({ type: UPDATE_PROJECT, updates: project })


// single family
const UPDATE_FAMILY = 'UPDATE_FAMILY'
export const familyState = {
  family: createSingleObjectReducer(UPDATE_FAMILY, {}, true),
}
export const getFamily = state => state.family
export const updateFamily = family => ({ type: UPDATE_FAMILY, updates: family })


// multiple families
const UPDATE_FAMILIES_BY_GUID = 'UPDATE_FAMILIES_BY_GUID'
export const familiesByGuidState = {
  familiesByGuid: createObjectsByIdReducer(UPDATE_FAMILIES_BY_GUID),
}
export const getFamiliesByGuid = state => state.familiesByGuid
export const updateFamiliesByGuid = familiesByGuid => ({ type: UPDATE_FAMILIES_BY_GUID, updatesById: familiesByGuid })


// multiple individuals
const UPDATE_INDIVIDUALS_BY_GUID = 'UPDATE_INDIVIDUALS_BY_GUID'
export const individualsByGuidState = {
  individualsByGuid: createObjectsByIdReducer(UPDATE_INDIVIDUALS_BY_GUID),
}
export const getIndividualsByGuid = state => state.individualsByGuid
export const updateIndividualsByGuid = individualsByGuid => ({ type: UPDATE_INDIVIDUALS_BY_GUID, updatesById: individualsByGuid })


//multiple samples
export const immutableSamplesByGuidState = {
  samplesByGuid: zeroActionsReducer,
}
export const getSamplesByGuid = state => state.samplesByGuid


// multiple datasets
export const immutableDatasetsByGuidState = {
  datasetsByGuid: zeroActionsReducer,
}
export const getDatasetsByGuid = state => state.datasetsByGuid

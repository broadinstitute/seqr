/* eslint-disable no-multi-spaces */

import { validators } from 'shared/components/form/ReduxFormWrapper'

//possible values
export const SHOW_ALL = 'SHOW_ALL'
export const SHOW_NEW = 'SHOW_NEW'

export const SORT_BY_PROJECT_NAME = 'SORT_BY_PROJECT_NAME'
export const SORT_BY_PROJECT_SAMPLES = 'SORT_BY_PROJECT_SAMPLES'
export const SORT_BY_NUM_FAMILIES = 'SORT_BY_NUM_FAMILIES'
export const SORT_BY_NUM_INDIVIDUALS = 'SORT_BY_NUM_INDIVIDUALS'
export const SORT_BY_DATE_CREATED = 'SORT_BY_DATE_CREATED'
export const SORT_BY_DATE_LAST_ACCESSED = 'SORT_BY_DATE_LAST_ACCESSED'
export const SORT_BY_TAGS = 'SORT_BY_TAGS'
export const SORT_BY_ANALYSIS = 'SORT_BY_ANALYSIS'

//export const SORT_BY_DATE_ACCESSED = 'SORT_BY_DATE_ACCESSED'

// modal
export const EDIT_NAME_MODAL = {
  form: 'editProjectName',
  fields: [
    { name: 'name', validate: validators.required, autoFocus: true },
  ],
}
export const EDIT_DESCRIPTION_MODAL =  {
  form: 'editProjectDescription',
  fields: [
    { name: 'description', autoFocus: true },
  ],
}
export const ADD_PROJECT_MODAL = {
  form: 'addProject',
  fields: [
    { name: 'name', label: 'Project Name', placeholder: 'Name', validate: validators.required, autoFocus: true },
    { name: 'description', label: 'Project Description', placeholder: 'Description' },
  ],
}


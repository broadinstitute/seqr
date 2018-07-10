import React from 'react'
import { Link } from 'react-router-dom'

import BaseFieldView from 'shared/components/panel/view-fields/BaseFieldView'
import OptionFieldView from 'shared/components/panel/view-fields/OptionFieldView'

const noSecondOptions = { year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: 'numeric' }

const BASE_FIELDS = [
  {
    field: 'name',
    fieldName: 'List Name',
    width: 3,
    isEditable: true,
    format: locusList => <Link to={`/gene_lists/${locusList.locusListGuid}`}>{locusList.name}</Link>,
  },
  {
    field: 'isPublic',
    fieldName: 'Public List',
    // fieldDisplay: isPublic => (isPublic ? 'Yes' : 'No'),
    width: 2,
    isEditable: true,
    component: OptionFieldView,
    tagOptions: [{ value: true, text: 'Yes' }, { value: false, text: 'No' }],
  },
  { field: 'numEntries', fieldName: 'Genes', width: 1, component: BaseFieldView },
  { field: 'description', fieldName: 'Description', width: 9, isEditable: true },
  {
    field: 'lastModifiedDate',
    fieldName: 'Last Updated',
    width: 3,
    fieldDisplay: lastModifiedDate => new Date(lastModifiedDate).toLocaleString('en-US', noSecondOptions),
  },
]

const fieldToCol = ({ field, fieldName, format, fieldDisplay, width }) => ({
  field,
  width: Math.min(width, 6),
  content: fieldName,
  format: format || (fieldDisplay ? val => fieldDisplay(val[field]) : null),
})

export const PUBLIC_FIELDS = BASE_FIELDS.concat([{ field: 'createdBy', fieldName: 'Curator', width: 3 }])
export const PRIVATE_FIELDS = BASE_FIELDS.concat([{ field: '', fieldName: '', width: 3 }])

export const PUBLIC_COLUMNS = PUBLIC_FIELDS.filter(field => field.field !== 'isPublic').map(fieldToCol)
export const PRIVATE_COLUMNS = PRIVATE_FIELDS.filter(field => field.field !== 'isPublic').map(fieldToCol)

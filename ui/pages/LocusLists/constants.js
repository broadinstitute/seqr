import React from 'react'
import { Link } from 'react-router-dom'

const BASE_FIELDS = [
  { field: 'name', fieldName: 'List Name', width: 3, format: locusList => <Link to={`/gene_lists/${locusList.locusListGuid}`}>{locusList.name}</Link> },
  { field: 'numEntries', fieldName: 'Genes', width: 1 },
  { field: 'description', fieldName: 'Description', width: 6 },
  { field: 'lastModifiedDate', fieldName: 'Last Updated', width: 3, fieldDisplay: lastModifiedDate => new Date(lastModifiedDate).toLocaleString() },
]

const fieldToCol = ({ field, fieldName, format, fieldDisplay, width }) => (
  { field, width, content: fieldName, format: format || (fieldDisplay ? val => fieldDisplay(val[field]) : null) }
)

export const PUBLIC_FIELDS = BASE_FIELDS.concat([{ field: 'createdBy', fieldName: 'Curator', width: 3 }])
export const PRIVATE_FIELDS = BASE_FIELDS.concat([{ field: '', fieldName: '', width: 3 }])

export const PUBLIC_COLUMNS = PUBLIC_FIELDS.map(fieldToCol)
export const PRIVATE_COLUMNS = PRIVATE_FIELDS.map(fieldToCol)

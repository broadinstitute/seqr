import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'

import { getLocusListsByGuid } from 'redux/selectors'
import { UpdateLocusListButton, DeleteLocusListButton } from '../buttons/LocusListButtons'
import SortableTable from './SortableTable'
import { LOCUS_LIST_FIELDS, LOCUS_LIST_IS_PUBLIC_FIELD_NAME } from '../../utils/constants'

const FIELDS = LOCUS_LIST_FIELDS.map(
  ({ name, label, fieldDisplay, width }) => ({
    name,
    width: Math.min(width, 6),
    content: label,
    format: fieldDisplay ? val => fieldDisplay(val[name]) : null,
  }),
)

const LocusListTable = ({ locusListsByGuid, showPublic, isEditable, showLinks, omitFields, selectRows }) => {
  let fields = FIELDS.filter(field => !omitFields.includes(field.name))
  if (showLinks) {
    fields[0].format = locusList => <Link to={`/gene_lists/${locusList.locusListGuid}`}>{locusList.name}</Link>
  }
  if (!showPublic && isEditable) {
    fields = fields.slice(0, fields.length - 1).concat([{
      name: '',
      format: locusList => ([
        <UpdateLocusListButton key="edit" locusList={locusList} />,
        <DeleteLocusListButton key="delete" iconOnly locusList={locusList} />,
      ]),
      width: 3,
    }])
  }
  return (
    <SortableTable
      basic="very"
      fixed
      idField="locusListGuid"
      defaultSortColumn="name"
      columns={fields}
      selectRows={selectRows}
      data={Object.values(locusListsByGuid).filter(locusList => locusList.isPublic === showPublic)}
    />
  )
}

LocusListTable.propTypes = {
  locusListsByGuid: PropTypes.object,
  showPublic: PropTypes.bool,
  isEditable: PropTypes.bool,
  showLinks: PropTypes.bool,
  selectRows: PropTypes.func,
  omitFields: PropTypes.array,
}

LocusListTable.defaultProps = {
  isEditable: true,
  showLinks: true,
  omitFields: [LOCUS_LIST_IS_PUBLIC_FIELD_NAME],
}

const mapStateToProps = state => ({
  locusListsByGuid: getLocusListsByGuid(state),
})

export default connect(mapStateToProps)(LocusListTable)

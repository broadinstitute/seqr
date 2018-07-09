import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getLocusListsByGuid } from 'redux/selectors'
import BaseFieldView from 'shared/components/panel/view-fields/BaseFieldView'

import { PUBLIC_FIELDS } from '../constants'

const LocusListDetail = ({ locusList }) =>
  <div>
    {locusList && PUBLIC_FIELDS.map(({ field, fieldName, fieldDisplay }) =>
      <div key={field}>
        <BaseFieldView
          field={field}
          fieldName={fieldName}
          fieldDisplay={fieldDisplay}
          idField="locusListGuid"
          initialValues={locusList}
          compact
          // isEditable: project.canEdit && field.canEdit,
          // onSubmit: submitFunc,
          // modalTitle: `${renderDetails.name} for Family ${family.displayName}`,
        />
      </div>,
    )}
  </div>

LocusListDetail.propTypes = {
  locusList: PropTypes.object,
}

const mapStateToProps = (state, ownProps) => ({
  locusList: getLocusListsByGuid(state)[ownProps.match.params.locusListGuid],
})

export default connect(mapStateToProps)(LocusListDetail)

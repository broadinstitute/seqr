import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Header, Grid } from 'semantic-ui-react'

import { updateLocusList } from 'redux/rootReducer'
import { getLocusListsByGuid } from 'redux/selectors'
import LocusListGeneDetail from 'shared/components/panel/genes/LocusListGeneDetail'
import BaseFieldView from 'shared/components/panel/view-fields/BaseFieldView'
import { LOCUS_LIST_FIELDS } from 'shared/utils/constants'

const getFieldProps = ({ isEditable, width, fieldDisplay, ...fieldProps }) => ({
  field: fieldProps.name,
  fieldName: fieldProps.label,
  formFields: [fieldProps],
  width,
  fieldDisplay,
  isEditable,
})

const FIELDS = LOCUS_LIST_FIELDS.map(getFieldProps)


const LocusListDetail = ({ locusList, onSubmit, match }) =>
  <div>
    <Grid>
      {FIELDS.map(({ isEditable, width, ...fieldProps }) =>
        <Grid.Column key={fieldProps.field} width={Math.max(width, 2)}>
          <BaseFieldView
            {...fieldProps}
            idField="locusListGuid"
            initialValues={locusList}
            onSubmit={onSubmit}
            isEditable={locusList.canEdit && isEditable}
            modalTitle={`Edit ${fieldProps.fieldName} for ${locusList.name}`}
            showEmptyValues
          />
        </Grid.Column>,
      )}
    </Grid>
    <LocusListGeneDetail locusListGuid={match.params.locusListGuid} locusList={locusList} />
    <Header size="medium" dividing>Intervals</Header>
    {/* TODO */}
  </div>

LocusListDetail.propTypes = {
  locusList: PropTypes.object,
  onSubmit: PropTypes.func,
  match: PropTypes.object,
}

const mapStateToProps = (state, ownProps) => ({
  locusList: getLocusListsByGuid(state)[ownProps.match.params.locusListGuid] || {},
})

const mapDispatchToProps = {
  onSubmit: updateLocusList,
}

export default connect(mapStateToProps, mapDispatchToProps)(LocusListDetail)

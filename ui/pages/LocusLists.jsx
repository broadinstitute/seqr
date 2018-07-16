import React from 'react'
import PropTypes from 'prop-types'
import { Route, Switch } from 'react-router-dom'
import { connect } from 'react-redux'
import { Container, Header, Grid } from 'semantic-ui-react'

import { updateLocusList } from 'redux/rootReducer'
import { getLocusListsByGuid } from 'redux/selectors'
import LocusListGeneDetail from 'shared/components/panel/genes/LocusListGeneDetail'
import BaseFieldView from 'shared/components/panel/view-fields/BaseFieldView'
import { LocusListsLoader } from 'shared/components/LocusListLoader'
import LocusListTables from 'shared/components/table/LocusListTables'
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


const BaseLocusListDetail = ({ locusList, onSubmit, match }) =>
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

BaseLocusListDetail.propTypes = {
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

const LocusListDetail = connect(mapStateToProps, mapDispatchToProps)(BaseLocusListDetail)


const LocusLists = ({ match }) =>
  <LocusListsLoader>
    <Container>
      <Switch>
        <Route path={`${match.url}/:locusListGuid`} component={LocusListDetail} />
        <Route path={`${match.url}`} component={LocusListTables} />
      </Switch>
    </Container>
  </LocusListsLoader>

LocusLists.propTypes = {
  match: PropTypes.object,
}

export default LocusLists

import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Header, Grid } from 'semantic-ui-react'

import { loadLocusLists } from 'redux/rootReducer'
import { getLocusListsByGuid, getLocusListIsLoading } from 'redux/selectors'
import DataLoader from 'shared/components/DataLoader'
import BaseFieldView from 'shared/components/panel/view-fields/BaseFieldView'
import ShowGeneModal from 'shared/components/buttons/ShowGeneModal'

import { PUBLIC_FIELDS } from '../constants'

const LocusListDetail = ({ locusList, load, loading, match }) =>
  <div>
    {PUBLIC_FIELDS.map(({ field, fieldName, fieldDisplay }) =>
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
    <Header size="medium" dividing>Genes</Header>
    <DataLoader contentId={match.params.locusListGuid} content={locusList.geneIds} loading={loading} load={load} hideError>
      {locusList.geneIds &&
        <Grid columns={12} divided="vertically">
          {locusList.geneIds.map(geneId =>
            <Grid.Column key={geneId}><ShowGeneModal geneId={geneId} /></Grid.Column>,
          )}
        </Grid>
      }
    </DataLoader>
    <Header size="medium" dividing>Intervals</Header>
    {/* TODO */}
  </div>

LocusListDetail.propTypes = {
  locusList: PropTypes.object,
  load: PropTypes.func,
  loading: PropTypes.bool,
  match: PropTypes.object,
}

const mapStateToProps = (state, ownProps) => ({
  locusList: getLocusListsByGuid(state)[ownProps.match.params.locusListGuid] || {},
  loading: getLocusListIsLoading(state),
})

const mapDispatchToProps = {
  load: loadLocusLists,
}

export default connect(mapStateToProps, mapDispatchToProps)(LocusListDetail)

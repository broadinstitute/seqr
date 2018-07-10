import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Header, Grid } from 'semantic-ui-react'

import { loadLocusLists } from 'redux/rootReducer'
import { getLocusListsByGuid, getLocusListIsLoading, getGenesById } from 'redux/selectors'
import DataLoader from 'shared/components/DataLoader'
import TextFieldView from 'shared/components/panel/view-fields/TextFieldView'
import ShowGeneModal from 'shared/components/buttons/ShowGeneModal'
import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'
import { compareObjects } from 'shared/utils/sortUtils'
import { toSnakecase } from 'shared/utils/stringUtils'

import { PUBLIC_FIELDS } from '../constants'

const LocusListDetail = ({ locusList, load, loading, genesById, match }) => {
  const genes = (locusList.geneIds || []).map(geneId => genesById[geneId]).sort(compareObjects('symbol'))
  const geneExportDownloads = [{
    name: 'Genes',
    data: {
      filename: toSnakecase(locusList.name),
      rawData: genes,
      processRow: gene => ([gene.geneId, gene.symbol]),
    },
  }]
  return (
    <div>
      <Grid>
        {PUBLIC_FIELDS.map(({ field, fieldName, format, width, isEditable, component, ...fieldProps }) =>
          <Grid.Column key={field} width={Math.max(width, 2)}>
            {
              React.createElement(component || TextFieldView, {
                field,
                fieldName,
                idField: 'locusListGuid',
                initialValues: locusList,
                showEmptyValues: true,
                isEditable: locusList.canEdit && isEditable,
                onSubmit: console.log,
                modalTitle: `Edit ${fieldName} for ${locusList.name}`,
                ...fieldProps,
              })
            }
          </Grid.Column>,
        )}
      </Grid>
      <Header size="medium" dividing>
        Genes <ExportTableButton downloads={geneExportDownloads} buttonText="Download" float="right" fontWeight="300" fontSize=".75em" />
      </Header>
      <DataLoader contentId={match.params.locusListGuid} content={locusList.geneIds} loading={loading} load={load}>
        <Grid columns={12} divided="vertically">
          {genes.map(gene =>
            <Grid.Column key={gene.geneId}><ShowGeneModal gene={gene} /></Grid.Column>,
          )}
        </Grid>
      </DataLoader>
      <Header size="medium" dividing>Intervals</Header>
      {/* TODO */}
    </div>
  )
}

LocusListDetail.propTypes = {
  locusList: PropTypes.object,
  load: PropTypes.func,
  loading: PropTypes.bool,
  genesById: PropTypes.object,
  match: PropTypes.object,
}

const mapStateToProps = (state, ownProps) => ({
  locusList: getLocusListsByGuid(state)[ownProps.match.params.locusListGuid] || {},
  loading: getLocusListIsLoading(state),
  genesById: getGenesById(state),
})

const mapDispatchToProps = {
  load: loadLocusLists,
}

export default connect(mapStateToProps, mapDispatchToProps)(LocusListDetail)

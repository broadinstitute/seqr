import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Header, Grid } from 'semantic-ui-react'

import { updateLocusList } from 'redux/rootReducer'
import { getLocusListsByGuid } from 'redux/selectors'
import BaseFieldView from '../view-fields/BaseFieldView'
import ShowGeneModal from '../../buttons/ShowGeneModal'
import ExportTableButton from '../../buttons/export-table/ExportTableButton'
import { toSnakecase } from '../../../utils/stringUtils'
import { LOCUS_LIST_GENE_FIELD } from '../../../utils/constants'
import { LocusListGeneLoader } from '../../LocusListLoader'

const getFieldProps = ({ isEditable, width, fieldDisplay, ...fieldProps }) => ({
  field: fieldProps.name,
  fieldName: fieldProps.label,
  formFields: [fieldProps],
  width,
  fieldDisplay,
  isEditable,
})

const GENE_FIELD = getFieldProps(LOCUS_LIST_GENE_FIELD)


const LocusListGeneDetail = ({ locusList, onSubmit }) => {
  const geneExportDownloads = [{
    name: 'Genes',
    data: {
      filename: toSnakecase(locusList.name),
      rawData: locusList.genes,
      processRow: gene => ([gene.geneId, gene.symbol]),
    },
  }]
  return (
    <div>
      <Header size="medium" dividing>
        <BaseFieldView
          {...GENE_FIELD}
          idField="locusListGuid"
          initialValues={locusList}
          onSubmit={onSubmit}
          isEditable={locusList.canEdit}
          compact
          modalTitle={`Edit Genes for ${locusList.name}`}
          showErrorPanel
        />
        <ExportTableButton downloads={geneExportDownloads} buttonText="Download" float="right" fontWeight="300" fontSize=".75em" />
      </Header>
      <Grid columns={12} divided="vertically">
        {(locusList.genes || []).map(gene =>
          <Grid.Column key={gene.geneId}><ShowGeneModal gene={gene} /></Grid.Column>,
        )}
      </Grid>
    </div>
  )
}

LocusListGeneDetail.propTypes = {
  locusList: PropTypes.object,
  onSubmit: PropTypes.func,
  locusListGuid: PropTypes.string,
  genes: PropTypes.array,
}


const LoadedLocusListGeneDetail = ({ locusListGuid, locusList, projectGuid, onSubmit }) =>
  <LocusListGeneLoader locusListGuid={locusListGuid} locusList={locusList} projectGuid={projectGuid}>
    <LocusListGeneDetail locusList={locusList} onSubmit={onSubmit} />
  </LocusListGeneLoader>

LoadedLocusListGeneDetail.propTypes = {
  locusListGuid: PropTypes.string.isRequired,
  locusList: PropTypes.object,
  onSubmit: PropTypes.func,
  projectGuid: PropTypes.string,
}

const mapStateToProps = (state, ownProps) => ({
  locusList: getLocusListsByGuid(state)[ownProps.locusListGuid] || {},
})

const mapDispatchToProps = {
  onSubmit: updateLocusList,
}

export default connect(mapStateToProps, mapDispatchToProps)(LoadedLocusListGeneDetail)

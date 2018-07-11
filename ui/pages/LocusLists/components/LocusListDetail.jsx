import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Header, Grid } from 'semantic-ui-react'

import { updateLocusList } from 'redux/rootReducer'
import { getLocusListsByGuid } from 'redux/selectors'
import BaseFieldView from 'shared/components/panel/view-fields/BaseFieldView'
import ShowGeneModal from 'shared/components/buttons/ShowGeneModal'
import ExportTableButton from 'shared/components/buttons/export-table/ExportTableButton'
import { toSnakecase } from 'shared/utils/stringUtils'
import { LOCUS_LIST_FIELDS, LOCUS_LIST_GENE_FIELD } from 'shared/utils/constants'
import LocusListGeneLoader from './LocusListGeneLoader'

const getFieldProps = ({ isEditable, width, fieldDisplay, ...fieldProps }) => ({
  field: fieldProps.name,
  fieldName: fieldProps.label,
  formFields: [fieldProps],
  width,
  fieldDisplay,
  isEditable,
})

const FIELDS = LOCUS_LIST_FIELDS.map(getFieldProps)

const GENE_FIELD = getFieldProps(LOCUS_LIST_GENE_FIELD)


const GeneDetails = ({ locusList, onSubmit }) => {
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

GeneDetails.propTypes = {
  locusList: PropTypes.object,
  onSubmit: PropTypes.func,
  locusListGuid: PropTypes.string,
  genes: PropTypes.array,
}


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
    <LocusListGeneLoader locusListGuid={match.params.locusListGuid} locusList={locusList}>
      <GeneDetails locusList={locusList} onSubmit={onSubmit} />
    </LocusListGeneLoader>
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

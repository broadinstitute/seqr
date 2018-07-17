import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Header, Grid } from 'semantic-ui-react'

import { updateLocusList } from 'redux/rootReducer'
import { getLocusListsByGuid } from 'redux/selectors'
import BaseFieldView from '../view-fields/BaseFieldView'
import ShowGeneModal from '../../buttons/ShowGeneModal'
import ExportTableButton from '../../buttons/export-table/ExportTableButton'
import { toSnakecase } from '../../../utils/stringUtils'
import { LOCUS_LIST_FIELDS, LOCUS_LIST_GENE_FIELD, LOCUS_LIST_INTERVAL_FIELD } from '../../../utils/constants'
import { LocusListGeneLoader } from '../../LocusListLoader'

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
const INTERVAL_FIELD = getFieldProps(LOCUS_LIST_INTERVAL_FIELD)

const CompactColumn = styled(Grid.Column)`
  padding-bottom: 0 !important;
`

const LocusListDetail = ({ locusList, onSubmit }) => {
  const geneExportDownloads = [{
    name: 'Genes',
    data: {
      headers: ['Gene ID', 'Symbol'],
      filename: `${toSnakecase(locusList.name)}_genes`,
      rawData: locusList.genes,
      processRow: gene => ([gene.geneId, gene.symbol]),
    },
  }]
  const intervalExportDownloads = [{
    name: 'Intervals',
    data: {
      headers: ['Chromosome', 'Start', 'End', 'Genome Version'],
      filename: `${toSnakecase(locusList.name)}_intervals`,
      rawData: locusList.intervals,
      processRow: interval => ([interval.chrom, interval.start, interval.end, interval.genomeVersion]),
    },
  }]
  const sharedFieldProps = {
    idField: 'locusListGuid',
    initialValues: locusList,
    onSubmit,
    isEditable: locusList.canEdit,
    showEmptyValues: true,
  }
  return (
    <div>
      <Grid>
        {FIELDS.map(({ isEditable, width, ...fieldProps }) =>
          <CompactColumn key={fieldProps.field} width={Math.max(width, 2)}>
            <BaseFieldView
              {...fieldProps}
              {...sharedFieldProps}
              isEditable={locusList.canEdit && isEditable}
              modalTitle={`Edit ${fieldProps.fieldName} for "${locusList.name}"`}
            />
          </CompactColumn>,
        )}
      </Grid>
      <Header size="medium" dividing>
        <BaseFieldView
          {...GENE_FIELD}
          {...sharedFieldProps}
          modalTitle={`Edit Genes for "${locusList.name}"`}
          compact
          showErrorPanel
        />
        <ExportTableButton downloads={geneExportDownloads} buttonText="Download" float="right" fontWeight="300" fontSize=".75em" />
      </Header>
      <Grid columns={12} divided="vertically">
        {(locusList.genes || []).map(gene =>
          <Grid.Column key={gene.geneId}><ShowGeneModal gene={gene} /></Grid.Column>,
        )}
      </Grid>
      <Header size="medium" dividing>
        <BaseFieldView
          {...INTERVAL_FIELD}
          {...sharedFieldProps}
          modalTitle={`Edit Intervals for "${locusList.name}"`}
          compact
          showErrorPanel
        />
        <ExportTableButton downloads={intervalExportDownloads} buttonText="Download" float="right" fontWeight="300" fontSize=".75em" />
      </Header>
      <Grid columns={8} divided="vertically">
        {(locusList.intervals || []).map(interval =>
          <Grid.Column key={interval.locusListIntervalGuid}>chr{interval.chrom}:{interval.start}-{interval.end}</Grid.Column>,
        )}
      </Grid>
    </div>
  )
}

LocusListDetail.propTypes = {
  locusList: PropTypes.object,
  onSubmit: PropTypes.func,
  locusListGuid: PropTypes.string,
  genes: PropTypes.array,
}


const LoadedLocusListDetail = ({ locusListGuid, locusList, projectGuid, onSubmit }) =>
  <LocusListGeneLoader locusListGuid={locusListGuid} locusList={locusList} projectGuid={projectGuid}>
    <LocusListDetail locusList={locusList} onSubmit={onSubmit} />
  </LocusListGeneLoader>

LoadedLocusListDetail.propTypes = {
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

export default connect(mapStateToProps, mapDispatchToProps)(LoadedLocusListDetail)

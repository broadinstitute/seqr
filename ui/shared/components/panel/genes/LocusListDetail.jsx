import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Header, Grid } from 'semantic-ui-react'

import { updateLocusList } from 'redux/rootReducer'
import { getParsedLocusList } from 'redux/selectors'
import BaseFieldView from '../view-fields/BaseFieldView'
import ShowGeneModal from '../../buttons/ShowGeneModal'
import ExportTableButton from '../../buttons/export-table/ExportTableButton'
import { toSnakecase } from '../../../utils/stringUtils'
import { LOCUS_LIST_FIELDS, LOCUS_LIST_ITEMS_FIELD } from '../../../utils/constants'
import { LocusListItemsLoader } from '../../LocusListLoader'

const getFieldProps = ({ isEditable, width, fieldDisplay, additionalFormFields, ...fieldProps }) => ({
  field: fieldProps.name,
  fieldName: fieldProps.label,
  formFields: [fieldProps, ...(additionalFormFields || [])],
  width,
  fieldDisplay,
  isEditable,
})

const FIELDS = LOCUS_LIST_FIELDS.map(getFieldProps)
const ITEMS_FIELD = getFieldProps(LOCUS_LIST_ITEMS_FIELD)

const CompactColumn = styled(Grid.Column)`
  padding-bottom: 0 !important;
`

const LocusListDetail = ({ locusList, onSubmit }) => {
  const itemExportDownloads = [
    {
      name: 'Genes',
      data: {
        headers: ['Gene ID', 'Symbol'],
        filename: `${toSnakecase(locusList.name)}_genes`,
        rawData: locusList.items.filter(item => item.geneId),
        processRow: item => ([item.geneId, item.display]),
      },
    },
    {
      name: 'Intervals',
      data: {
        headers: ['Chromosome', 'Start', 'End', 'Genome Version'],
        filename: `${toSnakecase(locusList.name)}_intervals`,
        rawData: locusList.items.filter(item => item.chrom),
        processRow: item => ([item.chrom, item.start, item.end, item.genomeVersion]),
      },
    },
  ]
  const { items, ...locusListMetadata } = locusList
  const itemsValues = { ...locusListMetadata, rawItems: items.map(({ display }) => display).join(', ') }
  const sharedFieldProps = {
    idField: 'locusListGuid',
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
              initialValues={locusListMetadata}
              isEditable={locusList.canEdit && isEditable}
              modalTitle={`Edit ${fieldProps.fieldName} for "${locusList.name}"`}
            />
          </CompactColumn>,
        )}
      </Grid>
      <Header size="medium" dividing>
        <BaseFieldView
          {...ITEMS_FIELD}
          {...sharedFieldProps}
          initialValues={itemsValues}
          modalTitle={`Edit Genes and Intervals for "${locusList.name}"`}
          compact
          showErrorPanel
        />
        <ExportTableButton downloads={itemExportDownloads} buttonText="Download" float="right" fontWeight="300" fontSize=".75em" />
      </Header>
      <Grid columns={8}>
        {items.length ?
          items.map(({ display, gene }) =>
            <Grid.Column key={display}>
              {gene ? <ShowGeneModal gene={gene} /> : display}
            </Grid.Column>,
          ) : <Grid.Column width={16}><i>This list has no entries</i></Grid.Column>
        }
      </Grid>
    </div>
  )
}

LocusListDetail.propTypes = {
  locusList: PropTypes.object,
  onSubmit: PropTypes.func,
  locusListGuid: PropTypes.string,
}


const LoadedLocusListDetail = ({ locusListGuid, locusList, onSubmit }) =>
  <LocusListItemsLoader locusListGuid={locusListGuid} locusList={locusList}>
    <LocusListDetail locusList={locusList} onSubmit={onSubmit} />
  </LocusListItemsLoader>

LoadedLocusListDetail.propTypes = {
  locusListGuid: PropTypes.string.isRequired,
  locusList: PropTypes.object,
  onSubmit: PropTypes.func,
}

const mapStateToProps = (state, ownProps) => ({
  locusList: getParsedLocusList(state, ownProps),
})

const mapDispatchToProps = {
  onSubmit: updateLocusList,
}

export default connect(mapStateToProps, mapDispatchToProps)(LoadedLocusListDetail)

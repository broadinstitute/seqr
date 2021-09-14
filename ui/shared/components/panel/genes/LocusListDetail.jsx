import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Header, Grid } from 'semantic-ui-react'

import { updateLocusList } from 'redux/rootReducer'
import BaseFieldView from '../view-fields/BaseFieldView'
import { DeleteLocusListButton } from '../../buttons/LocusListButtons'
import ShowGeneModal from '../../buttons/ShowGeneModal'
import ExportTableButton from '../../buttons/ExportTableButton'
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

const LocusListDetail = React.memo(({ locusList, onSubmit }) => {
  const itemExportDownloads = [
    {
      name: 'Genes',
      headers: ['Gene ID', 'Symbol'],
      filename: `${toSnakecase(locusList.name)}_genes`,
      rawData: locusList.items.filter(item => item.geneId),
      processRow: item => ([item.geneId, item.display]),
    },
    {
      name: 'Intervals',
      headers: ['Chromosome', 'Start', 'End', 'Genome Version'],
      filename: `${toSnakecase(locusList.name)}_intervals`,
      rawData: locusList.items.filter(item => item.chrom),
      processRow: item => ([item.chrom, item.start, item.end, item.genomeVersion]),
    },
  ]
  const { items, ...itemsValues } = locusList
  const { rawItems, ...locusListMetadata } = itemsValues
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
        {locusList.canEdit &&
          <CompactColumn key="delete" width={2}>
            <DeleteLocusListButton locusList={locusList} />
          </CompactColumn>
        }
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
        <ExportTableButton downloads={itemExportDownloads} buttonText="Download" floated="right" fontWeight="300" />
      </Header>
      <Grid columns={8}>
        {items.length ?
          items.map(({ display, gene, pagene }) =>
            <Grid.Column key={display}>
              {gene ? <ShowGeneModal gene={gene} pagene={pagene} /> : display}
            </Grid.Column>,
          ) : <Grid.Column width={16}><i>This list has no entries</i></Grid.Column>
        }
      </Grid>
    </div>
  )
})

LocusListDetail.propTypes = {
  locusList: PropTypes.object,
  onSubmit: PropTypes.func,
  locusListGuid: PropTypes.string,
}


const LoadedLocusListDetail = React.memo(({ locusListGuid, onSubmit }) =>
  <LocusListItemsLoader locusListGuid={locusListGuid}>
    <LocusListDetail onSubmit={onSubmit} />
  </LocusListItemsLoader>,
)

LoadedLocusListDetail.propTypes = {
  locusListGuid: PropTypes.string.isRequired,
  onSubmit: PropTypes.func,
}

const mapDispatchToProps = {
  onSubmit: updateLocusList,
}

export default connect(null, mapDispatchToProps)(LoadedLocusListDetail)

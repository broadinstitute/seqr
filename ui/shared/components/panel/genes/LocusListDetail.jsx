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
import { LOCUS_LIST_FIELDS, LOCUS_LIST_ITEMS_FIELD } from '../../../utils/constants'
import { LocusListItemsLoader } from '../../LocusListLoader'

const getFieldProps = ({ isEditable, width, fieldDisplay, ...fieldProps }) => ({
  field: fieldProps.name,
  fieldName: fieldProps.label,
  formFields: [fieldProps],
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
        rawData: locusList.parsedItems.items.filter(item => item.geneId),
        processRow: gene => ([gene.geneId, gene.symbol]),
      },
    },
    {
      name: 'Intervals',
      data: {
        headers: ['Chromosome', 'Start', 'End', 'Genome Version'],
        filename: `${toSnakecase(locusList.name)}_intervals`,
        rawData: locusList.parsedItems.items.filter(item => item.chrom),
        processRow: interval => ([interval.chrom, interval.start, interval.end, interval.genomeVersion]),
      },
    },
  ]
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
          {...ITEMS_FIELD}
          {...sharedFieldProps}
          modalTitle={`Edit Genes and Intervals for "${locusList.name}"`}
          compact
          showErrorPanel
        />
        <ExportTableButton downloads={itemExportDownloads} buttonText="Download" float="right" fontWeight="300" fontSize=".75em" />
      </Header>
      <Grid columns={8}>
        {(Object.keys(locusList.parsedItems.itemMap).length) ?
          Object.keys(locusList.parsedItems.itemMap).sort().map(itemDisplay =>
            <Grid.Column key={itemDisplay}>
              {locusList.parsedItems.itemMap[itemDisplay].geneId ?
                <ShowGeneModal gene={locusList.parsedItems.itemMap[itemDisplay]} /> : itemDisplay
              }
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
  locusList: getLocusListsByGuid(state)[ownProps.locusListGuid] || {},
})

const mapDispatchToProps = {
  onSubmit: updateLocusList,
}

export { LocusListDetail }
export default connect(mapStateToProps, mapDispatchToProps)(LoadedLocusListDetail)

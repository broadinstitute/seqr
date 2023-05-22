import React from 'react'
import PropTypes from 'prop-types'

import { RNASEQ_JUNCTION_PADDING } from 'shared/utils/constants'
import { camelcaseToTitlecase } from 'shared/utils/stringUtils'
import { GeneSearchLink } from 'shared/components/buttons/SearchResultsLink'
import DataTable from 'shared/components/table/DataTable'
import { COVERAGE_TYPE, JUNCTION_TYPE } from 'shared/components/panel/family/constants'
import ShowGeneModal from 'shared/components/buttons/ShowGeneModal'
import { ButtonLink } from 'shared/components/StyledComponents'
import { getLocus } from 'shared/components/panel/variants/VariantUtils'

const RNA_SEQ_SPLICE_NUM_FIELDS = ['zScore', 'pValue', 'deltaPsi']
const RNA_SEQ_SPLICE_DETAIL_FIELDS = ['type', 'readCount', 'rareDiseaseSamplesWithJunction', 'rareDiseaseSamplesTotal']

const openReads = (updateReads, row) => () => {
  const { chrom, start, end, tissueType, familyGuid } = row
  updateReads(familyGuid, getLocus(chrom, start, RNASEQ_JUNCTION_PADDING, end - start),
    [JUNCTION_TYPE, COVERAGE_TYPE], tissueType)
}

export const RNA_SEQ_SPLICE_COLUMNS = [
  {
    name: 'junctionLocus',
    content: 'Junction',
    width: 4,
    format: (row, isExport, updateReads) => (
      <div>
        <ButtonLink onClick={openReads(updateReads, row)}>
          {row.junctionLocus}
        </ButtonLink>
        <GeneSearchLink
          buttonText=""
          icon="search"
          location={`${row.chrom}:${Math.max(1, row.start - RNASEQ_JUNCTION_PADDING)}-${row.end + RNASEQ_JUNCTION_PADDING}`}
          familyGuid={row.familyGuid}
        />
      </div>
    ),
  }, {
    name: 'gene',
    content: 'Gene',
    width: 2,
    format: row => (
      <div>
        <ShowGeneModal gene={row} />
        <GeneSearchLink
          buttonText=""
          icon="search"
          location={row.geneId}
          familyGuid={row.familyGuid}
          floated="right"
        />
      </div>
    ),
  },
  ...RNA_SEQ_SPLICE_NUM_FIELDS.map(name => (
    {
      name,
      content: camelcaseToTitlecase(name).replace(' ', '-'),
      format: row => row[name].toPrecision(3),
    }
  )),
  ...RNA_SEQ_SPLICE_DETAIL_FIELDS.map(name => (
    {
      name,
      content: camelcaseToTitlecase(name).replace(' ', '-'),
    }
  )),
]

const RnaSeqJunctionOutliersTable = React.memo(
  ({ variant, reads, showReads, updateReads, data, columns, dispatch, ...props }) => (
    <div>
      {reads}
      <DataTable
        idField="idField"
        columns={columns || RNA_SEQ_SPLICE_COLUMNS}
        data={data}
        formatProps={updateReads}
        {...props}
      />
    </div>
  ),
)

RnaSeqJunctionOutliersTable.propTypes = {
  variant: PropTypes.object,
  reads: PropTypes.object,
  showReads: PropTypes.object,
  updateReads: PropTypes.func,
  data: PropTypes.arrayOf(PropTypes.object),
  columns: PropTypes.arrayOf(PropTypes.object),
  dispatch: PropTypes.func,
}

export default RnaSeqJunctionOutliersTable

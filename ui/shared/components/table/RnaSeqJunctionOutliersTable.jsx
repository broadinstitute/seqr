import React from 'react'
import { Popup, Icon } from 'semantic-ui-react'
import PropTypes from 'prop-types'

import { RNASEQ_JUNCTION_PADDING, TISSUE_DISPLAY } from 'shared/utils/constants'
import { camelcaseToTitlecase } from 'shared/utils/stringUtils'
import { GeneSearchLink } from 'shared/components/buttons/SearchResultsLink'
import DataTable from 'shared/components/table/DataTable'
import { COVERAGE_TYPE, JUNCTION_TYPE } from 'shared/components/panel/family/constants'
import ShowGeneModal from 'shared/components/buttons/ShowGeneModal'
import { ButtonLink } from 'shared/components/StyledComponents'
import { getLocus } from 'shared/components/panel/variants/VariantUtils'

const RNA_SEQ_SPLICE_NUM_FIELDS = ['zScore', 'pValue', 'deltaPsi']
const RNA_SEQ_SPLICE_DETAIL_FIELDS = ['type', 'readCount']

const openReads = (updateReads, row) => () => {
  const { chrom, start, end, tissueType, familyGuid } = row
  updateReads(familyGuid, getLocus(chrom, start, RNASEQ_JUNCTION_PADDING, end - start),
    [JUNCTION_TYPE, COVERAGE_TYPE], tissueType)
}

const JUNCTION_COLUMN = {
  name: 'junctionLocus',
  content: 'Junction',
  width: 4,
  format: (row, isExport, updateReads) => (
    <div>
      <ButtonLink onClick={openReads(updateReads, row)}>
        {`${row.chrom}:${row.start}-${row.end} ${row.strand}`}
      </ButtonLink>
      <GeneSearchLink
        buttonText=""
        icon="search"
        location={getLocus(row.chrom, row.start, RNASEQ_JUNCTION_PADDING, row.end - row.start)}
        familyGuid={row.familyGuid}
      />
    </div>
  ),
}

const GENE_COLUMN = {
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
}

const OTHER_SPLICE_COLUMNS = [
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
  {
    name: 'rareDiseaseSamplesWithJunction',
    content: (
      <Popup
        content="Rare-Disease Samples With Junction"
        position="top center"
        trigger={
          <span>
            RD Junctions
            <Icon name="info circle" />
          </span>
        }
      />
    ),
  },
  {
    name: 'rareDiseaseSamplesTotal',
    content: (
      <Popup
        content="Rare-Disease Samples Total"
        position="top right"
        trigger={
          <span>
            RD Total
            <Icon name="info circle" />
          </span>
        }
      />
    ),
  },
]

const RNA_SEQ_SPLICE_COLUMNS = [
  JUNCTION_COLUMN,
  GENE_COLUMN,
  ...OTHER_SPLICE_COLUMNS,
]

const INDIVIDUAL_NAME_COLUMN = { name: 'individualName', content: '', format: ({ individualName }) => (<b>{individualName}</b>) }

const RNA_SEQ_SPLICE_POPUP_COLUMNS = [
  INDIVIDUAL_NAME_COLUMN,
  {
    ...JUNCTION_COLUMN,
    format: ({ chrom, start, end, strand }) => `${chrom}:${start}-${end} ${strand}`,
  },
  {
    name: 'tissueType',
    content: 'Tissue Type',
    format: ({ tissueType }) => TISSUE_DISPLAY[tissueType],
  },
  ...OTHER_SPLICE_COLUMNS,
]

const RnaSeqJunctionOutliersTable = React.memo(
  ({ variant, reads, showReads, updateReads, data, showPopupColumns, dispatch, ...props }) => (
    <div>
      {reads}
      <DataTable
        idField="idField"
        columns={showPopupColumns ? RNA_SEQ_SPLICE_POPUP_COLUMNS : RNA_SEQ_SPLICE_COLUMNS}
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
  showPopupColumns: PropTypes.bool,
  dispatch: PropTypes.func,
}

export default RnaSeqJunctionOutliersTable

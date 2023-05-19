import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import { getIndividualsByGuid } from 'redux/selectors'
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

const RNA_SEQ_SPLICE_COLUMNS = [
  {
    name: 'junctionLocus',
    content: 'Junction',
    width: 4,
    format: (row, isExport, { onClickCell, familyGuid }) => (
      <div>
        <ButtonLink onClick={onClickCell(row, familyGuid)}>
          {row.junctionLocus}
        </ButtonLink>
        {familyGuid && (
          <GeneSearchLink
            buttonText=""
            icon="search"
            location={`${row.chrom}:${Math.max(1, row.start - RNASEQ_JUNCTION_PADDING)}-${row.end + RNASEQ_JUNCTION_PADDING}`}
            familyGuid={familyGuid}
          />
        )}
      </div>
    ),
  }, {
    name: 'gene',
    content: 'Gene',
    width: 2,
    format: (row, isExport, { familyGuid }) => (
      <div>
        {familyGuid ? <ShowGeneModal gene={row} /> : row.geneSymbol}
        {familyGuid && (
          <GeneSearchLink
            buttonText=""
            icon="search"
            location={row.geneId}
            familyGuid={familyGuid}
            floated="right"
          />
        )}
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

const formatProps = {}

const RnaSeqJunctionOutliersTable = React.memo(
  ({ data, reads, familyGuidForFormat, showReads, updateReads, individualsByGuid, dispatch, ...props }) => {
    const openReads = (row, familyGuid) => () => {
      const { chrom, start, end, tissueType, individualGuid } = row
      const openFamilyGuid = familyGuid || individualsByGuid[individualGuid].familyGuid
      updateReads(openFamilyGuid, getLocus(chrom, start, RNASEQ_JUNCTION_PADDING, end - start),
        [JUNCTION_TYPE, COVERAGE_TYPE], tissueType)
    }

    Object.assign(formatProps, { onClickCell: openReads, familyGuid: familyGuidForFormat })

    return (
      <div>
        {reads}
        <DataTable
          idField="idField"
          columns={RNA_SEQ_SPLICE_COLUMNS}
          data={data}
          formatProps={formatProps}
          {...props}
        />
      </div>
    )
  },
)

RnaSeqJunctionOutliersTable.propTypes = {
  variant: PropTypes.object,
  reads: PropTypes.object,
  updateReads: PropTypes.func,
  showReads: PropTypes.object,
  data: PropTypes.arrayOf(PropTypes.object),
  familyGuidForFormat: PropTypes.string,
  individualsByGuid: PropTypes.object,
  dispatch: PropTypes.func,
}

const mapStateToProps = state => ({
  individualsByGuid: getIndividualsByGuid(state),
})

export default connect(mapStateToProps, null)(RnaSeqJunctionOutliersTable)

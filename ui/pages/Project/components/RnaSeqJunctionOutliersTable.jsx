import React from 'react'
import PropTypes from 'prop-types'

import { RNASEQ_JUNCTION_PADDING } from 'shared/utils/constants'
import { camelcaseToTitlecase } from 'shared/utils/stringUtils'
import { GeneSearchLink } from 'shared/components/buttons/SearchResultsLink'
import DataTable from 'shared/components/table/DataTable'
import FamilyReads from 'shared/components/panel/family/FamilyReads'
import { COVERAGE_TYPE, JUNCTION_TYPE } from 'shared/components/panel/family/constants'
import ShowGeneModal from 'shared/components/buttons/ShowGeneModal'
import { ButtonLink } from 'shared/components/StyledComponents'
import { getLocus } from 'shared/components/panel/variants/VariantUtils'

const RNA_SEQ_SPLICE_NUM_FIELDS = ['zScore', 'pValue', 'deltaPsi']
const RNA_SEQ_SPLICE_DETAIL_FIELDS = ['type', 'readCount', 'rareDiseaseSamplesWithJunction', 'rareDiseaseSamplesTotal']

const RNA_SEQ_SPLICE_COLUMNS = [
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

const getJunctionLocus = (junction) => {
  const size = junction.end && junction.end - junction.start
  return getLocus(junction.chrom, junction.start, RNASEQ_JUNCTION_PADDING, size)
}

class BaseRnaSeqJunctionOutliersTable extends React.PureComponent {

  static propTypes = {
    reads: PropTypes.object,
    updateReads: PropTypes.func,
    data: PropTypes.arrayOf(PropTypes.object),
    familyGuid: PropTypes.string,
    tissueType: PropTypes.string,
  }

  openReads = row => () => {
    const { updateReads, familyGuid, tissueType } = this.props
    updateReads(familyGuid, getJunctionLocus(row), [JUNCTION_TYPE, COVERAGE_TYPE], tissueType)
  }

  render() {
    const { data, reads, familyGuid } = this.props
    const junctionColumns = [{
      name: 'junctionLocus',
      content: 'Junction',
      width: 4,
      format: row => (
        <div>
          <ButtonLink onClick={this.openReads(row)}>
            {row.junctionLocus}
          </ButtonLink>
          <GeneSearchLink
            buttonText=""
            icon="search"
            location={`${row.chrom}:${Math.max(1, row.start - RNASEQ_JUNCTION_PADDING)}-${row.end + RNASEQ_JUNCTION_PADDING}`}
            familyGuid={familyGuid}
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
            familyGuid={familyGuid}
            floated="right"
          />
        </div>
      ),
    }].concat(RNA_SEQ_SPLICE_COLUMNS)

    return (
      <div>
        {reads}
        <DataTable
          data={data}
          idField="idField"
          columns={junctionColumns}
          defaultSortColumn="pValue"
          maxHeight="600px"
        />
      </div>
    )
  }

}

const RnaSeqJunctionOutliersTable = props => (
  <FamilyReads layout={BaseRnaSeqJunctionOutliersTable} noTriggerButton {...props} />
)

export default RnaSeqJunctionOutliersTable

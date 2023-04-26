import React from 'react'
import PropTypes from 'prop-types'

import { camelcaseToTitlecase } from 'shared/utils/stringUtils'
import { GeneSearchLink } from 'shared/components/buttons/SearchResultsLink'
import DataTable from 'shared/components/table/DataTable'
import FamilyReads from 'shared/components/panel/family/FamilyReads'
import { COVERAGE_TYPE, JUNCTION_TYPE } from 'shared/components/panel/family/constants'
import { ButtonLink } from 'shared/components/StyledComponents'

const RNA_SEQ_SPLICE_NUM_FIELDS = ['zScore', 'pValue', 'deltaPsi']
const RNA_SEQ_SPLICE_LOC_FIELDS = ['chrom', 'start', 'end', 'strand']
const RNA_SEQ_SPLICE_DETAIL_FIELDS = ['type', 'readCount', 'rareDiseaseSamplesWithJunction', 'rareDiseaseSamplesTotal']

const RNA_SEQ_SPLICE_COLUMNS = [
  {
    name: 'geneId',
    content: 'Gene-ID',
    format: row => (
      <GeneSearchLink
        buttonText={row.geneId}
        location={row.geneId}
        familyGuid={row.familyGuid}
        floated="right"
      />
    ),
  },
  ...RNA_SEQ_SPLICE_NUM_FIELDS.map(name => (
    {
      name,
      content: camelcaseToTitlecase(name).replace(' ', '-'),
      format: row => row[name].toPrecision(3),
    }
  )),
  ...RNA_SEQ_SPLICE_LOC_FIELDS.map(name => (
    {
      name,
      format: row => (
        <ButtonLink
          padding="0 0 0 1em"
          onClick={row.setVariant(row)}
          content={row[name]}
        />
      ),
    }
  )),
  ...RNA_SEQ_SPLICE_DETAIL_FIELDS.map(name => (
    {
      name,
      content: camelcaseToTitlecase(name).replace(' ', '-'),
    }
  )),
]

const LayoutReads = ({ reads }) => <div>{reads}</div>

LayoutReads.propTypes = {
  reads: PropTypes.object,
}

const IGV_SAMPLE_TYPES = [JUNCTION_TYPE, COVERAGE_TYPE]

class RnaSeqOutliersTable extends React.PureComponent {

  static propTypes = {
    rnaSeqData: PropTypes.object,
    familyGuid: PropTypes.string,
  }

  state = {
    variants: {},
  }

  setVariant = junctionRow => () => {
    const { chrom, start, end, pValue } = junctionRow || {}
    const key = `${chrom}-${start}-${end}`
    const { variants } = this.state
    this.setState({ variants: { ...variants, [key]: variants[key] ? null : { chrom, pos: start, end, pValue } } })
  }

  render() {
    const { rnaSeqData, familyGuid } = this.props

    const { variants } = this.state
    return (
      <div>
        {Object.entries(variants).filter(([, variant]) => variant)
          .sort((a, b) => a.pValue - b.pValue)
          .map(([key, variant]) => (
            <FamilyReads
              key={key}
              layout={LayoutReads}
              variant={variant}
              familyGuid={familyGuid}
              defaultSampleTypes={IGV_SAMPLE_TYPES}
            />
          ))}
        <DataTable
          data={Object.values(rnaSeqData || {}).filter(({ isSignificant }) => isSignificant)
            .sort((a, b) => a.pValue - b.pValue).splice(0, 50)
            .map(row => ({ familyGuid, setVariant: this.setVariant, ...row }))}
          idField="geneId"
          columns={RNA_SEQ_SPLICE_COLUMNS}
        />
      </div>
    )
  }

}
export default RnaSeqOutliersTable

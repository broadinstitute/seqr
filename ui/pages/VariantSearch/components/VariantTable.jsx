/* eslint-disable */
import React from 'react'
import PropTypes from 'prop-types'

import styled from 'styled-components'
import { connect } from 'react-redux'
//import { Table } from 'semantic-ui-react'

import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'

import { updateVariants } from '../reducers/rootReducer'
//import { HorizontalSpacer } from 'shared/components/Spacers'

/*
import {
  SORT_BY_CLINVAR_PATHOGENICITY,
} from '../constants'
*/
/*
const TABLE_IS_EMPTY_ROW = <Table.Row>
  <Table.Cell />
  <Table.Cell style={{ padding: '10px' }}>0 variants</Table.Cell>
</Table.Row>
*/


const TableContainer = styled.div`
  display: flex;
  flex-direction: column;
`

const TableRow = styled.div`
  display: flex;
  flex-direction: row;
  align-items: center;
  flex-wrap: wrap;
  padding: 3px 5px;
  
  //&:hover, &[style]:hover {
  //  border: 1px solid gray;
    //background: #EEF8FF !important;  
  //}
`

class VariantTable extends React.Component {

  static propTypes = {
    //user: PropTypes.object.isRequired,
    project: PropTypes.object.isRequired,
    variants: PropTypes.object.isRequired,
    //variantTableState: PropTypes.object.isRequired,
    updateVariants: PropTypes.func.isRequired,
  }

  constructor(props) {
    super(props)

    this.state = {
      nextPage: 1,
      isLoading: false,
    }

    this.httpRequestHelper = new HttpRequestHelper(
      `/api/project/${this.props.project.projectGuid}/query_variants`,
      this.handleHttpSuccess,
      this.handleHttpError,
    )
  }

  handleHttpSuccess = (response) => {
    this.props.updateVariants(response.variants)
    this.setState({ isLoading: false })
  }

  handleHttpError = (response) => {
    this.setState({ isLoading: false })
    console.error(response)
  }

  handleSearchChange = () => {
    this.props.updateVariants({})

    const { nextPage } = this.state
    const searchParams = { page: nextPage, limit: 100, family: '12345' }

    this.httpRequestHelper.post({ q: searchParams })
    this.setState({ isLoading: true, nextPage: nextPage + 1 })
  }

  componentDidMount() {
    this.handleSearchChange()
  }

  render() {
    const {
      variants,
      //showModal,
    } = this.props

    return (
      <TableContainer>
        {
          variants &&
          Object.values(variants).map((variant) => {
            return (
              <TableRow>
                <div>
                  {`${variant.chrom}:${variant.start} ${variant.ref} > ${variant.alt}`}
                </div>
                <div>
                  {variant.vep_consequences && variant.vep_consequences[0].replace('_', ' ')}
                </div>
                <div>
                  {variant.vep_transcript_id && variant.vep_transcript_id[0].replace('_', ' ')}
                </div>
                <div />
                <div />
              </TableRow>)
          })
        }
      </TableContainer>
    )
  }
}

const mapStateToProps = ({
  //user,
  project,
  variants,
}) => ({
  //user,
  project,
  variants,
})


const mapDispatchToProps = {
  updateVariants,
}

export default connect(mapStateToProps, mapDispatchToProps)(VariantTable)

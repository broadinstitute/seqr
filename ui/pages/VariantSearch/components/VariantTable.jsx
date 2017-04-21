import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'
import { Button, Table } from 'semantic-ui-react'

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

class VariantTable extends React.Component {

  static propTypes = {
    //user: React.PropTypes.object.isRequired,
    project: React.PropTypes.object.isRequired,
    variants: React.PropTypes.object.isRequired,
    //variantTableState: React.PropTypes.object.isRequired,
    updateVariants: React.PropTypes.func.isRequired,
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
    console.log('received', response.variants)
    this.props.updateVariants(response.variants)
    this.setState({ isLoading: false })
  }

  handleHttpError = (response) => {
    this.setState({ isLoading: false })
    console.error(response)
  }

  handleSearchChange = () => {
    this.props.updateVariants({ variants: [] })

    const nextPage = this.state.nextPage
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

    console.log('variants:', Object.keys(variants))
    return <div>
      <div style={{ marginLeft: '10px' }}>
        <b>Dataset:</b> Cohen <br /><br />
        <Button content="Search" onClick={this.handleSearchChange} />
        <br />
        <br />
        <span style={{ fontSize: '12pt', fontWeight: '600' }}>
          Variants:
        </span>
      </div>
      <Table striped stackable style={{ width: '100%' }}>
        <Table.Header>
          <Table.HeaderCell collapsing />
          <Table.HeaderCell collapsing><div style={{ paddingRight: '10px' }} className="text-column-header">Variant</div></Table.HeaderCell>
          <Table.HeaderCell collapsing><div style={{ paddingRight: '10px' }} className="text-column-header">Consequence</div></Table.HeaderCell>
          <Table.HeaderCell collapsing><div style={{ paddingRight: '10px' }} className="text-column-header">Gene</div></Table.HeaderCell>
          <Table.HeaderCell />
          <Table.HeaderCell collapsing />
        </Table.Header>
        <Table.Body>
          {
            variants.variants &&
            variants.variants.map((variant, i) => {
              return <Table.Row key={i}>
                <Table.Cell />
                <Table.Cell>
                  {`${variant.chrom}:${variant.start} ${variant.ref} > ${variant.alt}`}
                </Table.Cell>
                <Table.Cell>
                  {variant.vep_consequences && variant.vep_consequences[0].replace('_', ' ')}
                </Table.Cell>
                <Table.Cell>
                  {variant.vep_transcript_id && variant.vep_transcript_id[0].replace('_', ' ')}
                </Table.Cell>
                <Table.Cell />
                <Table.Cell />
              </Table.Row>
            })
          }
          {
            this.state.isLoading &&
            <Table.Row>
              <Table.Cell />
              <Table.Cell />
              <Table.Cell >
                Loading ...
              </Table.Cell>
              <Table.Cell />
              <Table.Cell />
              <Table.Cell />
            </Table.Row>
          }
        </Table.Body>
      </Table>
    </div>
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


const mapDispatchToProps = dispatch => bindActionCreators({ updateVariants }, dispatch)

export default connect(mapStateToProps, mapDispatchToProps)(VariantTable)

import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'

import { CASE_REVIEW_STATUS_OPTIONS } from '../../../constants'
import { updateIndividualsByGuid } from '../../../reducers/rootReducer'

import SaveStatus from '../../../../../shared/components/form/SaveStatus'
import { HorizontalSpacer } from '../../../../../shared/components/Spacers'
import { HttpRequestHelper } from '../../../../../shared/utils/httpRequestHelper'

class CaseReviewStatusDropdown extends React.Component {
  static propTypes = {
    individual: React.PropTypes.object.isRequired,
    updateIndividualsByGuid: React.PropTypes.func.isRequired,
  }

  constructor(props) {
    super(props)

    this.state = { saveStatus: SaveStatus.NONE, saveErrorMessage: null }

    this.httpRequestHelper = new HttpRequestHelper(
      '/api/individuals/save_case_review_status',
      this.handleSaveSuccess,
      this.handleSaveError,
      this.handleSaveClear,
    )
  }

  handleSaveSuccess = (responseJson) => {
    const individualsByGuid = responseJson
    this.props.updateIndividualsByGuid(individualsByGuid)
    if (this.mounted) {
      this.setState({ saveStatus: SaveStatus.SUCCEEDED })
    }
  }

  handleSaveError = (e) => {
    console.log('ERROR', e)
    if (this.mounted) {
      this.setState({ saveStatus: SaveStatus.ERROR, saveErrorMessage: e.message.toString() })
    }
  }

  handleSaveClear = () => {
    if (this.mounted) {
      this.setState({ saveStatus: SaveStatus.NONE, saveErrorMessage: null })
    }
  }

  componentWillMount() {
    this.mounted = true
  }

  componentWillUnmount() {
    this.mounted = false
  }

  render() {
    return <div className="nowrap" style={{ display: 'inline' }}>
      <select
        name={this.props.individual.individualGuid}
        value={this.props.individual.caseReviewStatus}
        onChange={(e) => {
          const selectedValue = e.target.value
          this.httpRequestHelper.post({ form: { [this.props.individual.individualGuid]: selectedValue } })
        }}
        tabIndex="1"
        style={{ margin: '3px !important', maxWidth: '170px', display: 'inline' }}
      >
        {
          CASE_REVIEW_STATUS_OPTIONS.map((option, k) =>
            <option key={k} value={option.value}>{option.name}</option>)
        }
      </select>
      <HorizontalSpacer width={5} />
      <SaveStatus status={this.state.saveStatus} errorMessage={this.state.saveErrorMessage} />
    </div>
  }
}

const mapDispatchToProps = dispatch => bindActionCreators({ updateIndividualsByGuid }, dispatch)

export default connect(null, mapDispatchToProps)(CaseReviewStatusDropdown)

import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import { Checkbox } from 'semantic-ui-react'
import SaveStatus from 'shared/components/form/SaveStatus'
import EditTextButton from 'shared/components/buttons/edit-text/EditTextButton'

import { HorizontalSpacer } from 'shared/components/Spacers'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { EDIT_INDIVIDUAL_INFO_MODAL_ID } from './EditIndividualInfoModal'
import { updateIndividualsByGuid } from '../../../reducers/rootReducer'
import {
  CASE_REVIEW_STATUS_OPTIONS,
  CASE_REVIEW_STATUS_ACCEPTED,
  CASE_REVIEW_STATUS_MORE_INFO_NEEDED,
  CASE_REVIEW_STATUS_ACCEPTED_FOR_OPTIONS,
} from '../../../constants'

class CaseReviewStatusDropdown extends React.Component {
  static propTypes = {
    individual: PropTypes.object.isRequired,
    updateIndividualsByGuid: PropTypes.func.isRequired,
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

  /**
   * Posts UI changes to the server.
   *
   * @param changes An object with required key: 'individualGuid',
   *    and optional keys: 'caseReviewStatus', 'caseReviewStatusAcceptedFor'
   */
  handleOnChange = (changes) => {
    if (this.mounted) {
      this.setState({ saveStatus: SaveStatus.IN_PROGRESS })
    }
    this.httpRequestHelper.post({ form: changes })
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
    const i = this.props.individual

    return <div className="nowrap" style={{ display: 'inline' }}>
      <select
        name={i.individualGuid}
        value={i.caseReviewStatus}
        onChange={(e) => {
          const selectedValue = e.target.value
          this.handleOnChange({ [i.individualGuid]: { action: 'UPDATE_CASE_REVIEW_STATUS', value: selectedValue } })
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
      {/* accepted-for checkboxes: */}
      {
        i.caseReviewStatus === CASE_REVIEW_STATUS_ACCEPTED ?
          <div className="checkbox-container">
            {CASE_REVIEW_STATUS_ACCEPTED_FOR_OPTIONS.map((option, k) => (
              option !== '---' ?
                <Checkbox
                  key={k}
                  label={option.name}
                  defaultChecked={i.caseReviewStatusAcceptedFor && i.caseReviewStatusAcceptedFor.includes(option.value)}
                  onChange={(e, result) => {
                    this.handleOnChange(
                      { [i.individualGuid]: { action: result.checked ? 'ADD_ACCEPTED_FOR' : 'REMOVE_ACCEPTED_FOR', value: option.value } },
                    )
                  }}
                /> : <br key={k} />
            ))}
          </div>
          : null
      }
      {/* edit case review discussion for individual: */}
      <div>
        {
          i.caseReviewStatus === CASE_REVIEW_STATUS_MORE_INFO_NEEDED &&
          <EditTextButton
            allowRichText
            label={'Edit Questions'}
            initialText={i.caseReviewDiscussion}
            modalTitle={`${i.individualId}: Case Review Discussion`}
            modalSubmitUrl={`/api/individual/${i.individualGuid}/update/caseReviewDiscussion`}
            modalId={EDIT_INDIVIDUAL_INFO_MODAL_ID}
          />
        }
      </div>
    </div>
  }
}

export { CaseReviewStatusDropdown as CaseReviewStatusDropdownComponent }

const mapDispatchToProps = {
  updateIndividualsByGuid,
}

export default connect(null, mapDispatchToProps)(CaseReviewStatusDropdown)

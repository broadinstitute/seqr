/* eslint-disable react/no-array-index-key */

import React from 'react'
import PropTypes from 'prop-types'

import { connect } from 'react-redux'
import { Checkbox } from 'semantic-ui-react'
import RequestStatus from 'shared/components/form/RequestStatus'
import EditTextButton from 'shared/components/buttons/EditTextButton'
import { EDIT_INDIVIDUAL_INFO_MODAL_ID } from 'shared/components/panel/edit-one-of-many-individuals/EditIndividualInfoModal'
import { HorizontalSpacer } from 'shared/components/Spacers'
import { HttpRequestHelper } from 'shared/utils/httpRequestHelper'
import { updateIndividualsByGuid } from 'redux/utils/commonDataActionsAndSelectors'

import {
  CASE_REVIEW_STATUS_ACCEPTED,
  CASE_REVIEW_STATUS_MORE_INFO_NEEDED,
  CASE_REVIEW_STATUS_OPTIONS,
} from 'shared/constants/caseReviewConstants'


import { CASE_REVIEW_STATUS_ACCEPTED_FOR_OPTIONS } from '../../../constants'

class CaseReviewStatusDropdown extends React.Component {
  static propTypes = {
    individual: PropTypes.object.isRequired,
    updateIndividualsByGuid: PropTypes.func.isRequired,
  }

  constructor(props) {
    super(props)

    this.state = { saveStatus: RequestStatus.NONE, saveErrorMessage: null }

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
      this.setState({ saveStatus: RequestStatus.IN_PROGRESS })
    }
    this.httpRequestHelper.post({ form: changes })
  }

  handleSaveSuccess = (responseJson) => {
    const individualsByGuid = responseJson
    this.props.updateIndividualsByGuid(individualsByGuid)
    if (this.mounted) {
      this.setState({ saveStatus: RequestStatus.SUCCEEDED })
    }
  }

  handleSaveError = (e) => {
    console.log('ERROR', e)
    if (this.mounted) {
      this.setState({ saveStatus: RequestStatus.ERROR, saveErrorMessage: e.message.toString() })
    }
  }

  handleSaveClear = () => {
    if (this.mounted) {
      this.setState({ saveStatus: RequestStatus.NONE, saveErrorMessage: null })
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

    return (
      <div style={{ display: 'inline-block', whitespace: 'nowrap', minWidth: '220px' }}>
        <select
          name={i.individualGuid}
          defaultValue={i.caseReviewStatus}
          onChange={(e) => {
            const selectedValue = e.target.value
            this.handleOnChange({ [i.individualGuid]: { action: 'UPDATE_CASE_REVIEW_STATUS', value: selectedValue } })
          }}
          tabIndex="1"
          style={{ margin: '3px !important', maxWidth: '170px', display: 'inline-block', padding: '0px !important' }}
        >
          {
            CASE_REVIEW_STATUS_OPTIONS.map(option => <option key={option.value} value={option.value}>{option.name}</option>)
          }
        </select>
        <HorizontalSpacer width={5} />
        <RequestStatus status={this.state.saveStatus} errorMessage={this.state.saveErrorMessage} />
        {
          i.caseReviewStatus === CASE_REVIEW_STATUS_ACCEPTED ?
            <div className="checkbox-container">
              {CASE_REVIEW_STATUS_ACCEPTED_FOR_OPTIONS.map((option, k) => {
                  if (option === '---') {
                    return <br key={k} />
                  }

                  return <Checkbox
                    key={option.value}
                    label={option.name}
                    defaultChecked={i.caseReviewStatusAcceptedFor !== null && i.caseReviewStatusAcceptedFor.includes(option.value)}
                    onChange={(e, result) => {
                      this.handleOnChange(
                        { [i.individualGuid]: { action: result.checked ? 'ADD_ACCEPTED_FOR' : 'REMOVE_ACCEPTED_FOR', value: option.value } },
                      )
                    }}
                  />
                })
              }
            </div>
            : null
        }
        {/* edit case review discussion for individual: */}
        <div>
          {
            i.caseReviewStatus === CASE_REVIEW_STATUS_MORE_INFO_NEEDED &&
            <EditTextButton
              label="Edit Questions"
              initialText={i.caseReviewDiscussion}
              modalTitle={`${i.individualId}: Case Review Discussion`}
              modalSubmitUrl={`/api/individual/${i.individualGuid}/update/caseReviewDiscussion`}
              modalId={EDIT_INDIVIDUAL_INFO_MODAL_ID}
            />
          }
        </div>
      </div>)
  }
}

export { CaseReviewStatusDropdown as CaseReviewStatusDropdownComponent }

const mapDispatchToProps = {
  updateIndividualsByGuid,
}

export default connect(null, mapDispatchToProps)(CaseReviewStatusDropdown)

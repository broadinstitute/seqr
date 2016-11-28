import React from 'react'
import injectSheet from 'react-jss'
import { Icon } from 'semantic-ui-react'

import RichTextEditorModal from './RichTextEditorModal'

const styles = {
  familyInfoDiv: {
    paddingLeft: '20px',
    maxWidth: '550px',
    wordWrap: 'break-word',
  },
}


@injectSheet(styles)
class FamilyInfoView extends React.Component {

  static propTypes = {
    project: React.PropTypes.object.isRequired,
    family: React.PropTypes.object.isRequired,
    sheet: React.PropTypes.object,
    showDetails: React.PropTypes.bool,
  }

  constructor(props) {
    super(props)

    this.state = {
      showEditInternalSummaryModal: false,
      showEditInternalNotesModal: false,
      internalCaseReviewNotes: props.family.internalCaseReviewNotes,
      internalCaseReviewSummary: props.family.internalCaseReviewSummary,
      showDetails: props.showDetails,
    }
  }

  render() {
    const project = this.props.project
    const family = this.props.family
    const classNames = this.props.sheet.classes

    return <span>
      {(!this.props.showDetails && (family.shortDescription || family.aboutFamilyContent || family.analysisSummaryContent)) ?
        <div style={{ color: 'grey' }}>
          <i>Details Not Shown: &nbsp;
            {
              ((family.shortDescription ? 'Family Description, ' : '') +
              (family.aboutFamilyContent ? 'Analysis Notes, ' : '') +
              (family.analysisSummaryContent ? 'Analysis Summary, ' : '')).slice(0, -2)
            }
          </i><br /><br />
        </div> :
        null
      }
      {(family.shortDescription && this.props.showDetails) ?
        <div>
          <b>Family Description:</b> &nbsp;
          <div className={classNames.familyInfoDiv}>{family.shortDescription}</div><br />
        </div> :
        null
      }
      {(family.aboutFamilyContent && this.props.showDetails) ?
        <div>
          <b>Analysis Notes:</b> <br />
          <div
            className={classNames.familyInfoDiv}
            dangerouslySetInnerHTML={{ __html: family.aboutFamilyContent }}
          /><br />
        </div> :
        null
      }
      {(family.analysisSummaryContent && this.props.showDetails) ?
        <div>
          <b>Analysis Summary:</b> <br />
          <div
            className={classNames.familyInfoDiv}
            dangerouslySetInnerHTML={{ __html: family.analysisSummaryContent }}
          /><br />
        </div> :
        null
      }

      <b>Internal Notes:</b>
      <a
        tabIndex="0"
        onClick={() => this.setState({ showEditInternalNotesModal: true })}
        style={{ paddingLeft: '20px' }}
      >
        <Icon link name="write" />
      </a>
      { this.state.internalCaseReviewNotes ?
        <span><br />
          <div
            className={classNames.familyInfoDiv}
            dangerouslySetInnerHTML={{ __html: this.state.internalCaseReviewNotes }}
          />
        </span> :
        null
      }
      { this.state.showEditInternalNotesModal ?
        <RichTextEditorModal
          title={`Family ${family.familyId}: Internal Notes`}
          initialText={this.state.internalCaseReviewNotes}
          formSubmitUrl={`/api/project/${project.projectGuid}/family/${family.familyGuid}/save_internal_case_review_notes`}
          onClose={() => this.setState({ showEditInternalNotesModal: false })}
          onSave={(response, savedJson) => { this.setState({ internalCaseReviewNotes: savedJson.form }) }}
        /> : <br />
      }


      <b>Internal Summary:</b>
      <a
        tabIndex="0"
        onClick={() => this.setState({ showEditInternalSummaryModal: true })}
        style={{ paddingLeft: '20px' }}
      >
        <Icon link name="write" />
      </a>
      { this.state.internalCaseReviewSummary ?
        <span><br />
          <div
            className={classNames.familyInfoDiv}
            dangerouslySetInnerHTML={{ __html: this.state.internalCaseReviewSummary }}
          />
        </span> : <br />
      }
      { this.state.showEditInternalSummaryModal ?
        <RichTextEditorModal
          title={`Family ${family.familyId}: Internal Summary`}
          initialText={this.state.internalCaseReviewSummary}
          formSubmitUrl={`/api/project/${project.projectGuid}/family/${family.familyGuid}/save_internal_case_review_summary`}
          onClose={() => this.setState({ showEditInternalSummaryModal: false })}
          onSave={(response, savedJson) => { this.setState({ internalCaseReviewSummary: savedJson.form }) }}
        /> :
        null
      }
    </span>
  }
}


export default FamilyInfoView

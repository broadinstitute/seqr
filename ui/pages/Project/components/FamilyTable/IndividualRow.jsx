import React from 'react'
import PropTypes from 'prop-types'
import styled from 'styled-components'
import { connect } from 'react-redux'
import { Link } from 'react-router-dom'
import { Label, Popup } from 'semantic-ui-react'
import orderBy from 'lodash/orderBy'

import PedigreeIcon from 'shared/components/icons/PedigreeIcon'
import BaseFieldView from 'shared/components/panel/view-fields/BaseFieldView'
import TextFieldView from 'shared/components/panel/view-fields/TextFieldView'
import OptionFieldView from 'shared/components/panel/view-fields/OptionFieldView'
import PhenotipsDataPanel from 'shared/components/panel/PhenotipsDataPanel'
import Sample from 'shared/components/panel/sample'
import { FamilyLayout } from 'shared/components/panel/family'
import { ColoredIcon } from 'shared/components/StyledComponents'
import { VerticalSpacer } from 'shared/components/Spacers'

import { updateIndividual } from 'redux/rootReducer'
import { getSamplesByGuid, getCurrentProject } from 'redux/selectors'
import { SAMPLE_STATUS_LOADED, DATASET_TYPE_VARIANT_CALLS } from 'shared/utils/constants'
import { snakecaseToTitlecase } from 'shared/utils/stringUtils'
import { CASE_REVIEW_STATUS_MORE_INFO_NEEDED, CASE_REVIEW_STATUS_OPTIONS } from '../../constants'

import CaseReviewStatusDropdown from './CaseReviewStatusDropdown'


const Detail = styled.div`
  display: inline-block;
  padding: 5px 0 5px 5px;
  font-size: 11px;
  font-weight: 500;
  color: #999999;
`

const CaseReviewDropdownContainer = styled.div`
  float: right;
  width: 220px;
`

const FLAG_TITLE = {
  chimera: '% Chimera',
  contamination: '% Contamination',
  coverage_exome: '% 20X Coverage',
  coverage_genome: 'Mean Coverage',
}

const ratioLabel = (flag) => {
  const words = snakecaseToTitlecase(flag).split(' ')
  return `Ratio ${words[1]}/${words[2]}`
}

const CaseReviewStatus = ({ individual }) =>
  <CaseReviewDropdownContainer>
    <CaseReviewStatusDropdown individual={individual} />
    {
      individual.caseReviewStatusLastModifiedDate ? (
        <Detail>
          CHANGED ON {new Date(individual.caseReviewStatusLastModifiedDate).toLocaleDateString()}
          { individual.caseReviewStatusLastModifiedBy && ` BY ${individual.caseReviewStatusLastModifiedBy}` }
        </Detail>
      ) : null
    }
  </CaseReviewDropdownContainer>

CaseReviewStatus.propTypes = {
  individual: PropTypes.object.isRequired,
}

const MmeStatusLabel = ({ title, dateField, color, individual }) =>
  <Link to={`/project/${individual.projectGuid}/family_page/${individual.familyGuid}/matchmaker_exchange`}>
    <VerticalSpacer height={5} />
    <Label color={color} size="small">
      {title}: {new Date(individual[dateField]).toLocaleDateString()}
    </Label>
  </Link>

MmeStatusLabel.propTypes = {
  title: PropTypes.string,
  dateField: PropTypes.string,
  color: PropTypes.string,
  individual: PropTypes.object,
}

const DataDetails = ({ loadedSamples, individual }) =>
  <div>
    {loadedSamples.map((sample, i) =>
      <div key={sample.sampleGuid}>
        <Sample loadedSample={sample} isOutdated={i !== 0} />
      </div>,
    )}
    {individual.mmeSubmittedDate && (
      individual.mmeDeletedDate ? (
        <Popup
          flowing
          trigger={
            <MmeStatusLabel title="Removed from MME" dateField="mmeDeletedDate" color="red" individual={individual} />
          }
          content={
            <div>
              <b>Originally Submitted: </b>{new Date(individual.mmeSubmittedDate).toLocaleDateString()}
            </div>
          }
        />
      ) : <MmeStatusLabel title="Submitted to MME" dateField="mmeSubmittedDate" color="violet" individual={individual} />
    )
  }
  </div>

DataDetails.propTypes = {
  individual: PropTypes.object,
  loadedSamples: PropTypes.array,
}

class IndividualRow extends React.Component
{
  static propTypes = {
    project: PropTypes.object.isRequired,
    family: PropTypes.object.isRequired,
    individual: PropTypes.object.isRequired,
    samplesByGuid: PropTypes.object.isRequired,
    updateIndividual: PropTypes.func,
    editCaseReview: PropTypes.bool,
  }

  render() {
    const { project, family, individual, editCaseReview } = this.props

    const { displayName, paternalId, maternalId, sex, affected, createdDate, sampleGuids, caseReviewStatus, caseReviewDiscussion } = individual

    let loadedSamples = sampleGuids.map(
      sampleGuid => this.props.samplesByGuid[sampleGuid],
    ).filter(s =>
      s.datasetType === DATASET_TYPE_VARIANT_CALLS &&
      s.sampleStatus === SAMPLE_STATUS_LOADED,
    )
    loadedSamples = orderBy(loadedSamples, [s => s.loadedDate], 'desc')
    // only show first and latest samples
    loadedSamples.splice(1, loadedSamples.length - 2)

    const leftContent =
      <div>
        <div>
          <PedigreeIcon sex={sex} affected={affected} /> {displayName}
        </div>
        <div>
          {
            (!family.pedigreeImage && ((paternalId && paternalId !== '.') || (maternalId && maternalId !== '.'))) ? (
              <Detail>
                child of &nbsp;
                <i>{(paternalId && maternalId) ? `${paternalId} and ${maternalId}` : (paternalId || maternalId) }</i>
                <br />
              </Detail>
            ) : null
          }
          <Detail>
            ADDED {new Date(createdDate).toLocaleDateString().toUpperCase()}
          </Detail>
        </div>
      </div>

    const rightContent = editCaseReview ?
      <CaseReviewStatus individual={individual} /> :
      <DataDetails loadedSamples={loadedSamples} individual={individual} />

    const fields = [
      {
        content: (
          <OptionFieldView
            key="caseReviewStatus"
            isVisible={!editCaseReview}
            fieldName="Case Review Status"
            field="caseReviewStatus"
            idField="individualGuid"
            initialValues={individual}
            tagOptions={CASE_REVIEW_STATUS_OPTIONS}
            tagAnnotation={value => <ColoredIcon name="stop" color={value.color} />}
          />
        ),
      },
      {
        content: (
          <TextFieldView
            key="discussion"
            isVisible={
              caseReviewStatus === CASE_REVIEW_STATUS_MORE_INFO_NEEDED
              || (editCaseReview && caseReviewDiscussion) || false
            }
            fieldName={editCaseReview ? 'Case Review Discussion' : 'Discussion'}
            field="caseReviewDiscussion"
            idField="individualGuid"
            initialValues={individual}
          />
        ),
      },
      {
        content: (
          <TextFieldView
            key="notes"
            isEditable={project.canEdit}
            fieldName="Individual Notes"
            field="notes"
            idField="individualGuid"
            initialValues={individual}
            modalTitle={`Notes for Individual ${displayName}`}
            onSubmit={this.props.updateIndividual}
          />
        ),
      },
      {
        content: (
          <TextFieldView
            key="population"
            isEditable={false}
            fieldName="Imputed Population"
            field="population"
            idField="individualGuid"
            initialValues={individual}
          />
        ),
      },
      {
        content: (
          <BaseFieldView
            key="filterFlags"
            isEditable={false}
            fieldName="Sample QC Flags"
            field="filterFlags"
            idField="individualGuid"
            initialValues={individual}
            fieldDisplay={filterFlags => Object.entries(filterFlags).map(([flag, val]) =>
              <Label
                key={flag}
                basic
                horizontal
                color="orange"
                content={`${FLAG_TITLE[flag] || snakecaseToTitlecase(flag)}: ${parseFloat(val).toFixed(2)}`}
              />,
            )}
          />
        ),
      },
      {
        content: (
          <BaseFieldView
            key="popPlatformFilters"
            isEditable={false}
            fieldName="Population/Platform Specific Sample QC Flags"
            field="popPlatformFilters"
            idField="individualGuid"
            initialValues={individual}
            fieldDisplay={filterFlags => Object.keys(filterFlags).map(flag =>
              <Label
                key={flag}
                basic
                horizontal
                color="orange"
                content={flag.startsWith('r_') ? ratioLabel(flag) : snakecaseToTitlecase(flag.replace('n_', 'num._'))}
              />,
            )}
          />
        ),
      },
      {
        content: (
          <PhenotipsDataPanel
            key="phenotips"
            individual={individual}
            showDetails
            showEditPhenotipsLink={project.canEdit}
          />
        ),
      },
    ]

    return (
      <FamilyLayout
        fields={fields}
        fieldDisplay={field => field.content}
        leftContent={leftContent}
        rightContent={rightContent}
      />
    )
  }
}

export { IndividualRow as IndividualRowComponent }

const mapStateToProps = state => ({
  project: getCurrentProject(state),
  samplesByGuid: getSamplesByGuid(state),
})


const mapDispatchToProps = {
  updateIndividual,
}

export default connect(mapStateToProps, mapDispatchToProps)(IndividualRow)

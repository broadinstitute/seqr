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
import { getSamplesByGuid, getCurrentProject, getMmeSubmissionsByGuid } from 'redux/selectors'
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

const POPULATION_MAP = {
  AFR: 'African',
  AMR: 'Latino',
  ASJ: 'Ashkenazi Jewish',
  EAS: 'East Asian',
  FIN: 'European (Finnish)',
  MDE: 'Middle Eastern',
  NFE: 'European (non-Finnish)',
  OTH: 'Other',
  SAS: 'South Asian',
}

const ratioLabel = (flag) => {
  const words = snakecaseToTitlecase(flag).split(' ')
  return `Ratio ${words[1]}/${words[2]}`
}

const CaseReviewStatus = React.memo(({ individual }) =>
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
  </CaseReviewDropdownContainer>,
)

CaseReviewStatus.propTypes = {
  individual: PropTypes.object.isRequired,
}

const MmeStatusLabel = React.memo(({ title, dateField, color, individual, mmeSubmission }) =>
  <Link to={`/project/${individual.projectGuid}/family_page/${individual.familyGuid}/matchmaker_exchange`}>
    <VerticalSpacer height={5} />
    <Label color={color} size="small">
      {title}: {new Date(mmeSubmission[dateField]).toLocaleDateString()}
    </Label>
  </Link>,
)

MmeStatusLabel.propTypes = {
  title: PropTypes.string,
  dateField: PropTypes.string,
  color: PropTypes.string,
  individual: PropTypes.object,
  mmeSubmission: PropTypes.object,
}

const DataDetails = React.memo(({ loadedSamples, individual, mmeSubmission }) =>
  <div>
    {loadedSamples.map(sample =>
      <div key={sample.sampleGuid}>
        <Sample loadedSample={sample} isOutdated={!sample.isActive} />
      </div>,
    )}
    {mmeSubmission && (
      mmeSubmission.deletedDate ? (
        <Popup
          flowing
          trigger={
            <MmeStatusLabel title="Removed from MME" dateField="deletedDate" color="red" individual={individual} mmeSubmission={mmeSubmission} />
          }
          content={
            <div>
              <b>Originally Submitted: </b>{new Date(mmeSubmission.createdDate).toLocaleDateString()}
            </div>
          }
        />
      ) : <MmeStatusLabel title="Submitted to MME" dateField="lastModifiedDate" color="violet" individual={individual} mmeSubmission={mmeSubmission} />
    )
  }
  </div>,
)

DataDetails.propTypes = {
  mmeSubmission: PropTypes.object,
  individual: PropTypes.object,
  loadedSamples: PropTypes.array,
}

const IndividualRow = React.memo((
  { project, family, individual, editCaseReview, mmeSubmission, samplesByGuid, dispatchUpdateIndividual },
) => {
  const { displayName, paternalId, maternalId, sex, affected, createdDate, sampleGuids, caseReviewStatus, caseReviewDiscussion } = individual

  let loadedSamples = sampleGuids.map(
    sampleGuid => samplesByGuid[sampleGuid],
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
    <DataDetails loadedSamples={loadedSamples} individual={individual} mmeSubmission={mmeSubmission} />

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
          onSubmit={dispatchUpdateIndividual}
        />
      ),
    },
    {
      content: (
        <BaseFieldView
          key="population"
          isEditable={false}
          fieldName="Imputed Population"
          field="population"
          idField="individualGuid"
          initialValues={individual}
          fieldDisplay={population => POPULATION_MAP[population] || population}

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
})

IndividualRow.propTypes = {
  project: PropTypes.object.isRequired,
  family: PropTypes.object.isRequired,
  individual: PropTypes.object.isRequired,
  mmeSubmission: PropTypes.object,
  samplesByGuid: PropTypes.object.isRequired,
  dispatchUpdateIndividual: PropTypes.func,
  editCaseReview: PropTypes.bool,
}

export { IndividualRow as IndividualRowComponent }

const mapStateToProps = (state, ownProps) => ({
  project: getCurrentProject(state),
  samplesByGuid: getSamplesByGuid(state),
  mmeSubmission: getMmeSubmissionsByGuid(state)[ownProps.individual.mmeSubmissionGuid],
})


const mapDispatchToProps = {
  dispatchUpdateIndividual: updateIndividual,
}

export default connect(mapStateToProps, mapDispatchToProps)(IndividualRow)

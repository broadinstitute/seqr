import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { Dropdown, Form, Grid } from 'semantic-ui-react'

import { getProject, getFamiliesByGuid, getIndividualsByGuid } from 'shared/utils/commonSelectors'
import FormWrapper from 'shared/components/form/FormWrapper'
import styled from 'styled-components'

const HeaderColumn = styled(Grid.Column)`
  text-align: left;
  font-weight: 710;
  font-size: 1.12em;
  vertical-align: middle;
`

const FormGrid = styled(Grid)`
  max-height: 800px;
  overflow: scroll;
`

const FormColumn = styled(Grid.Column)`
  text-align: left;
  vertical-align: middle;
  white-space: nowrap;
`

const FamilyIdInput = styled(Form.Input)`
  .ui.input {
    width: 80% !important;
  }
`

const GridRow = styled(Grid.Row)`
  padding: 0.5rem 0;
`

const FormCheckbox = styled(Form.Checkbox)`
  position: relative;
  top: 3px;
  padding-right: 15px;
`


const FormDropdown = styled(Dropdown)`
  padding: .78571429em 2.1em .78571429em 1em !important;
  .text {
    font-weight: 400;
  }
  
  i {
    top: 0.7em !important;
  }
`


class EditIndividualsForm extends React.PureComponent
{
  static propTypes = {
    //user: PropTypes.object.isRequired,
    familiesByGuid: PropTypes.object.isRequired,
    individualsByGuid: PropTypes.object.isRequired,
    //project: PropTypes.object,
    handleSave: PropTypes.func,
    handleClose: PropTypes.func,
  }

  constructor(props) {
    super(props)

    const modifiedIndividualsByGuid = {}
    const individualsByGuidCheckboxState = {}
    let individualIds = []
    Object.values(props.individualsByGuid).forEach((individual) => {
      modifiedIndividualsByGuid[individual.individualGuid] = {}
      individualIds = individualIds.concat([individual.individualId])
      individualsByGuidCheckboxState[individual.individualGuid] = false
    })

    // modified values are only used for record keeping, and don't affect the UI, so they're stored outside of state.
    this.modifiedIndividualsByGuid = modifiedIndividualsByGuid
    this.individualIdsForAutocomplete = individualIds
    this.state = individualsByGuidCheckboxState
  }


  render() {
    let i = -1
    const numIndividuals = Object.keys(this.props.individualsByGuid).length

    return (
      <FormWrapper
        submitButtonText="Apply"
        performValidation={this.performValidation}
        handleSave={this.props.handleSave}
        handleClose={this.props.handleClose}
        size="small"
        confirmCloseIfNotSaved
        getFormDataJson={() => ({
          modifiedIndividuals: this.modifiedIndividualsByGuid,
          individualsToDelete: this.state,
        })}
      >
        <Grid>
          <GridRow key="header">
            <HeaderColumn width={3}>
              <FormCheckbox
                checked={Object.values(this.state).every(isChecked => isChecked)}
                onChange={(e, data) => {
                  const allCheckboxStates = {}
                  Object.keys(this.state).forEach((individualGuid) => {
                    allCheckboxStates[individualGuid] = data.checked
                  })
                  this.setState(allCheckboxStates)
                }}
              />
              Family Id
            </HeaderColumn>
            <HeaderColumn width={3}>
              Individual Id
            </HeaderColumn>
            <HeaderColumn width={3}>
              Paternal Id
            </HeaderColumn>
            <HeaderColumn width={3}>
              Maternal Id
            </HeaderColumn>
            <HeaderColumn width={2}>
              Sex
            </HeaderColumn>
            <HeaderColumn width={2}>
              Affected
            </HeaderColumn>
          </GridRow>
        </Grid>
        <FormGrid>
          {
            Object.values(this.props.familiesByGuid).map(family =>
              family.individualGuids.map((individualGuid) => {
                i += 1
                const individual = this.props.individualsByGuid[individualGuid]
                return (
                  <GridRow key={individualGuid}>
                    <FormColumn width={3}>
                      <FormCheckbox
                        tabIndex={i}
                        checked={this.state[individualGuid]}
                        onChange={(e, data) => {
                          this.setState({ [individualGuid]: data.checked })
                        }}
                      />
                      <FamilyIdInput
                        tabIndex={i + numIndividuals}
                        type="text"
                        defaultValue={family.familyId}
                        onChange={(e, data) => {
                          this.modifiedIndividualsByGuid[individualGuid].familyId = data.value
                        }}
                      />
                    </FormColumn>
                    <FormColumn width={3}>
                      <Form.Input
                        tabIndex={i + (2 * numIndividuals)}
                        type="text"
                        defaultValue={individual.individualId}
                        onChange={(e, data) => {
                          this.modifiedIndividualsByGuid[individualGuid].individualId = data.value
                        }}
                      />
                    </FormColumn>
                    <FormColumn width={3}>
                      <Form.Input
                        tabIndex={i + (3 * numIndividuals)}
                        type="text"
                        defaultValue={individual.paternalId}
                        onChange={(e, data) => {
                          this.modifiedIndividualsByGuid[individualGuid].paternalId = data.value
                        }}
                      />
                    </FormColumn>
                    <FormColumn width={3}>
                      <Form.Input
                        tabIndex={i + (4 * numIndividuals)}
                        type="text"
                        defaultValue={individual.maternalId}
                        options={this.individualIdsForAutocomplete}
                        onChange={(e, data) => {
                          this.modifiedIndividualsByGuid[individualGuid].maternalId = data.value
                        }}
                      />
                    </FormColumn>
                    <FormColumn width={2}>
                      <FormDropdown
                        tabIndex={i + (5 * numIndividuals)}
                        search
                        fluid
                        selection
                        name="sex"
                        defaultValue={individual.sex}
                        options={[
                          { key: 'M', value: 'M', text: 'Male' },
                          { key: 'F', value: 'F', text: 'Female' },
                          { key: 'U', value: 'U', text: 'Unknown' },
                        ]}
                        onChange={(event, data) => {
                          this.modifiedIndividualsByGuid[individualGuid].sex = data.value
                        }}
                      />
                    </FormColumn>
                    <FormColumn width={2}>
                      <FormDropdown
                        tabIndex={i + (6 * numIndividuals)}
                        search
                        fluid
                        selection
                        name="affected"
                        defaultValue={individual.sex}
                        options={[
                          { key: 'A', value: 'A', text: 'Affected' },
                          { key: 'N', value: 'N', text: 'Unaffected' },
                          { key: 'U', value: 'U', text: 'Unknown' },
                        ]}
                        onChange={(event, data) => {
                          this.modifiedIndividualsByGuid[individualGuid].affected = data.value
                        }}
                      />
                    </FormColumn>
                  </GridRow>
                )
            }))
          }

        </FormGrid>
      </FormWrapper>)
  }

  performValidation = () => {
    return { errors: [], warnings: [], info: [] }
  }
}

export { EditIndividualsForm as EditIndividualsFormComponent }

const mapStateToProps = state => ({
  project: getProject(state),
  familiesByGuid: getFamiliesByGuid(state),
  individualsByGuid: getIndividualsByGuid(state),
})

export default connect(mapStateToProps)(EditIndividualsForm)

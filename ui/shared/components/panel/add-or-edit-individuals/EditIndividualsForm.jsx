import React from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
//import { Table } from 'semantic-ui-react'

import { getProject, getFamiliesByGuid, getIndividualsByGuid } from 'shared/utils/commonSelectors'
import FormWrapper from 'shared/components/form/FormWrapper'
import styled from 'styled-components'

import EditIndividualsFormHeaderRow from './EditIndividualsFormHeaderRow'
import EditIndividualsFormRow from './EditIndividualsFormRow'

const Table = styled.table`

`

const TableBody = styled.tbody`
  display: block;
  max-height: 800px;
  overflow: auto;
`

const TableHeader = styled.thead`
  display:table;
  table-layout:fixed;
  width:100%;
  padding-top: 7px;
  padding-bottom: 7px;
`


class EditIndividualsForm extends React.Component
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
    Object.keys(props.individualsByGuid).forEach((individualGuid) => {
      modifiedIndividualsByGuid[individualGuid] = {}
    })

    // modified values are only used for record keeping, and don't affect the UI, so they're stored outside of state.
    this.modifiedIndividualsByGuid = modifiedIndividualsByGuid
    this.individualsToDelete = {}
  }

  shouldComponentUpdate() {
    return false
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
          individualsToDelete: this.individualsToDelete,
        })}
      >
        <Table>
          <TableHeader>
            <EditIndividualsFormHeaderRow
              headerCheckboxHandler={this.headerCheckboxHandler}
            />
          </TableHeader>
          <TableBody>
            {
              Object.values(this.props.familiesByGuid).map(family =>
                family.individualGuids.map((individualGuid) => {
                  i += 1
                  const individual = this.props.individualsByGuid[individualGuid]
                  console.log(individual, this.individualsToDelete)
                  return (
                    <EditIndividualsFormRow
                      key={individual.individualGuid}
                      index={i}
                      numIndividuals={numIndividuals}
                      individual={individual}
                      isCheckboxChecked={this.individualsToDelete[individual.individualGuid]}
                      family={family}
                      onInputChange={this.inputChangeHandler}
                      onCheckboxChange={this.checkboxChangeHandler}
                    />
                  )
              }))
            }
          </TableBody>
        </Table>
      </FormWrapper>)
  }

  headerCheckboxHandler = (e) => {
    const isChecked = e.target.checked
    console.log('headerCheckboxHandler', e, this.individualsToDelete.size)

    if (isChecked) {
      Object.keys(this.props.individualsByGuid).forEach((individualGuid) => {
        this.individualsToDelete[individualGuid] = true
      })
    } else {
      this.individualsToDelete = {}
    }

    [...document.getElementsByClassName('formCheckbox')].forEach((cb) => {
      cb.checked = isChecked
    })
    console.log('headerCheckboxHandler - set to', e, isChecked, this.individualsToDelete.size)
  }

  inputChangeHandler = (e) => {
    console.log('inputChangeHandler', e)
    this.modifiedIndividuals[e.target.id][e.target.name] = e.target.checked
  }

  checkboxChangeHandler = (e) => {
    const isChecked = e.target.checked
    console.log('checkboxChangeHandler', e, isChecked)
    if (isChecked) {
      this.individualsToDelete[e.target.id] = true
    } else {
      delete this.individualsToDelete[e.target.id]
    }
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

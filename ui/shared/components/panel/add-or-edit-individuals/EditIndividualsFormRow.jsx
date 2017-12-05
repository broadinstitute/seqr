/* eslint-disable react/no-multi-comp */

import React from 'react'
import PropTypes from 'prop-types'
//import { Table } from 'semantic-ui-react'
import styled from 'styled-components'

const TableRow = styled.tr`
  display:table;
  table-layout:fixed;
  width: 100%;
`

/**
const FormCheckbox = styled(Form.Checkbox)`
  position: relative;
  top: 3px;
  padding-right: 15px;
`
const FormInput = styled(Form.Input)`
  input {
    padding: 5px 10px !important;
  }
`

const FamilyIdInput = styled(FormInput)`
  .ui.input {
    width: 80% !important;
  }
`

const ThinDropdown = styled(Dropdown)`
  padding: 5px 10px !important;
`

const FormDropdown = styled(ThinDropdown)`
  .text {
    font-weight: 400;
  }

  i {
    top: 0.7em !important;
  }

  .search {
    padding: 3px 6px !important;
  }
`
*/

class EditIndividualsFormRow extends React.Component
{
  static propTypes = {
    family: PropTypes.object.isRequired,
    individual: PropTypes.object.isRequired,
    onInputChange: PropTypes.func,
    onCheckboxChange: PropTypes.func,
  }

  shouldComponentUpdate() {
    return false
  }

  render() {
    console.log('rendering EditIndividualsFormRow', this.props.individual)
    return (
      <TableRow>
        <td>
          <input
            type="checkbox"
            className="formCheckbox"
            id={this.props.individual.individualGuid}
            onChange={this.props.onCheckboxChange}
          />
          <input
            type="text"
            id={this.props.individual.individualGuid}
            defaultValue={this.props.family.familyId}
            onChange={this.props.onInputChange}
          />
        </td>
        <IndividualIdInput {...this.props} />
        <PaternalIdInput {...this.props} />
        <MaternalIdInput {...this.props} />
        {/*<SexInput {...this.props} />
        <AffectedStatusInput {...this.props} />*/}
      </TableRow>)
  }
}

class IndividualIdInput extends React.Component {
  static propTypes = {
    individual: PropTypes.object.isRequired,
    onChange: PropTypes.func,
  }

  shouldComponentUpdate() {
    return false
  }

  render() {
    return (
      <td>
        <input
          type="text"
          id={this.props.individual.individualGuid}
          defaultValue={this.props.individual.individualId}
          onChange={this.props.onChange}
        />
      </td>)
  }
}


class PaternalIdInput extends React.Component {
  static propTypes = {
    individual: PropTypes.object.isRequired,
    onChange: PropTypes.func,
  }

  shouldComponentUpdate() {
    return false
  }

  render() {
    return (
      <td>
        <input
          type="text"
          id={this.props.individual.individualGuid}
          defaultValue={this.props.individual.paternalId}
          onChange={this.props.onChange}
        />
      </td>)
  }
}

class MaternalIdInput extends React.Component {
  static propTypes = {
    individual: PropTypes.object.isRequired,
    onChange: PropTypes.func,
  }

  shouldComponentUpdate() {
    return false
  }

  render() {
    return (
      <td>
        <input
          type="text"
          id={this.props.individual.individualGuid}
          defaultValue={this.props.individual.maternalId}
          onChange={this.props.onChange}
        />
      </td>)
  }
}

/*
class SexInput extends React.Component {
  static propTypes = {
    individual: PropTypes.object.isRequired,
    onChange: PropTypes.func,
  }

  shouldComponentUpdate() {
    return false
  }

  render() {
    return (
      <Table.Cell width={2}>
        <FormDropdown
          id={this.props.individual.individualGuid}
          search
          fluid
          selection
          name="sex"
          defaultValue={this.props.individual.sex}
          options={[
            { key: 'M', value: 'M', text: 'Male' },
            { key: 'F', value: 'F', text: 'Female' },
            { key: 'U', value: 'U', text: 'Unknown' },
          ]}
          onChange={this.props.onChange}
        />
      </Table.Cell>)
  }
}

class AffectedStatusInput extends React.Component {
  static propTypes = {
    individual: PropTypes.object.isRequired,
    onChange: PropTypes.func,
  }

  shouldComponentUpdate() {
    return false
  }

  render() {
    return (
      <Table.Cell width={2}>
        <FormDropdown
          id={this.props.individual.individualGuid}
          search
          fluid
          selection
          name="affected"
          defaultValue={this.props.individual.affected}
          options={[
            { key: 'A', value: 'A', text: 'Affected' },
            { key: 'N', value: 'N', text: 'Unaffected' },
            { key: 'U', value: 'U', text: 'Unknown' },
          ]}
          onChange={this.props.onChange}
        />
      </Table.Cell>)
  }
}
*/
export default EditIndividualsFormRow

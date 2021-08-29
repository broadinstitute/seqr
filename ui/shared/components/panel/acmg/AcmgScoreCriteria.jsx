import React from 'react'
import { Table } from 'semantic-ui-react'
import PropTypes from 'prop-types'
import { GetNewScoreValue } from './AcmgCriteria'

const formatCriteria = (criteria) => {
  const formattedCriteria = []

  for (let i = 0; i < criteria.length; i++) {
    formattedCriteria.push(criteria[i])

    if (i !== criteria.length - 1) {
      formattedCriteria[i] += ', '
    }
  }

  return formattedCriteria
}

const AcmgScoreCriteria = (props) => {
  const { criteria, classification } = props

  return (
    <div>
      <Table celled padded>
        <Table.Header>
          <Table.Row>
            <Table.HeaderCell singleLine>Score</Table.HeaderCell>
            <Table.HeaderCell singleLine>Classification</Table.HeaderCell>
            <Table.HeaderCell>Criteria Applied</Table.HeaderCell>
          </Table.Row>
        </Table.Header>

        <Table.Body>
          <Table.Row>
            <Table.Cell width="1">{GetNewScoreValue(criteria)}</Table.Cell>
            <Table.Cell width="3">{classification}</Table.Cell>
            <Table.Cell>{criteria.length === 0 ? 'No criteria applied' : formatCriteria(criteria)}</Table.Cell>
          </Table.Row>
        </Table.Body>
      </Table>
    </div>
  )
}

AcmgScoreCriteria.propTypes = {
  criteria: PropTypes.array.isRequired,
  classification: PropTypes.string.isRequired,
}

export default AcmgScoreCriteria

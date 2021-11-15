import React from 'react'
import { Table } from 'semantic-ui-react'
import PropTypes from 'prop-types'
import { getNewScoreValue } from './AcmgCriteria'

const formatCriteria = (criteria) => {
  const formattedCriteria = []
  criteria.forEach((c, criteriaIdx) => {
    formattedCriteria.push(c)

    if (criteriaIdx !== criteria.length - 1) {
      formattedCriteria[criteriaIdx] += ', '
    }
  })

  return formattedCriteria
}

const AcmgScoreCriteria = (props) => {
  const { criteria, classify } = props

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
            <Table.Cell width="1">{getNewScoreValue(criteria)}</Table.Cell>
            <Table.Cell width="3">{classify}</Table.Cell>
            <Table.Cell>{criteria.length === 0 ? 'No criteria applied' : formatCriteria(criteria)}</Table.Cell>
          </Table.Row>
        </Table.Body>
      </Table>
    </div>
  )
}

AcmgScoreCriteria.propTypes = {
  criteria: PropTypes.arrayOf(PropTypes.string),
  classify: PropTypes.string.isRequired,
}

export default AcmgScoreCriteria

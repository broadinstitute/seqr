/* eslint no-undef: "warn" */

import React from 'react'
import {Table} from 'semantic-ui-react'

import Family from './Family'
import Individual from './Individual'


class CaseReviewTable extends React.Component {

    constructor(props) {
        super(props)
    }

    render() {
        const {
            project,
            families_by_id,
            individuals_by_id,
            family_id_to_indiv_ids
        } = this.props

        return <Table celled style={{width: "100%"}}>
                <Table.Body>
                {
                    Object.keys(families_by_id).map((family_id, family_i) => {
                        const backgroundColor = family_i % 2 == 0 ? 'white' : '#F3F3F3'
                        return <Table.Row key={family_id} style={{backgroundColor}}>

                            <Table.Cell style={{padding: "5px 0px 15px 15px"}}>
                                <Family project_id={project.project_id}
                                        family_id={family_id} {...families_by_id[family_id]}
                                />


                                {/* Individuals Table */}
                                <Table celled style={{
                                    width: '100%',
                                    margin: '0px',
                                    backgroundColor: 'transparent',
                                    borderWidth: '0px',
                                }}>
                                    <Table.Body>
                                    {
                                        family_id_to_indiv_ids[family_id].map((individual_id, individual_i) => {
                                            return <Table.Row key={individual_i}>
                                                <Table.Cell style={{padding: "10px 0px 0px 15px", borderWidth: "0px"}}>
                                                    <Individual project={project}
                                                        family={families_by_id[family_id]}
                                                        {... individuals_by_id[individual_id]}
                                                    />
                                                </Table.Cell>
                                            </Table.Row>
                                        })
                                    }
                                    </Table.Body>
                                </Table>
                            </Table.Cell>
                        </Table.Row>

                    })
                }
                </Table.Body>
            </Table>
    }
}
/*

CaseReviewTable.propTypes = {
    project: React.PropTypes.object.isRequired,
    families_by_id: React.PropTypes.object.isRequired,
    individuals_by_id: React.PropTypes.object.isRequired,
    family_id_to_indiv_ids: React.PropTypes.object.isRequired,
}
*/

export default CaseReviewTable

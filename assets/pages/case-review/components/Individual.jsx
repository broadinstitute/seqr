import React from 'react'
import {Grid, Icon} from 'semantic-ui-react'

import Modal from '../../../shared/components/Modal'



let CaseReviewStatusSelector = ({initialState}) =>
    <select value={initialState} name="case_review_status">
        <option value="">---</option>
        <option value="A">Accepted</option>
        <option value="E">Accepted: Exome</option>
        <option value="G">Accepted: Genome</option>
        <option value="R">Not Accepted</option>
        <option value="N">See Notes</option>
        <option value="H">Hold</option>
    </select>



class Individual extends React.Component
{
    constructor(props) {
        super(props)
    }

    render() {
        const {
            family,
            individual_id,
            paternal_id,
            maternal_id,
            sex,
            affected,
            phenotips,
            case_review_status,
            in_case_review
        } = this.props

        return <Grid stackable style={{width: "100%", padding:"15px 0px 15px 0px"}}>
            <Grid.Row style={{padding: "0px"}}>
                <Grid.Column width={13} style={{padding: "0px"}}>

                    <b>
                        <Icon style={{fontSize: "13px"}} name={
                         (
                            (sex==='U' || affected==='U') ?
                                'help':
                                (sex==='M'?'square':'circle')+(affected==='N'? (sex==='F'?' thin':' outline'):'')
                        )}/>
                    </b>

                    &nbsp;

                    {individual_id}
                    {
                        (!family.pedigree_image && (paternal_id || maternal_id)) ? (
                            <div style={{fontSize: "8pt"}}>
                                child of &nbsp;
                                <i>{(paternal_id && maternal_id) ? paternal_id + ", " + maternal_id : (paternal_id || maternal_id)}</i>
                            </div>) : null
                    }

                    <span style={{margin: "10px"}}/>

                    PhenoTips: {phenotips ? "" : " -- "}
                    [<a href="google.com">PDF</a>]

                </Grid.Column>

                <Grid.Column width={3}>
                    <CaseReviewStatusSelector initialState={case_review_status}/>
                </Grid.Column>
            </Grid.Row>
        </Grid>

    }
}

Individual.propTypes = {
    family: React.PropTypes.object,
    paternalId: React.PropTypes.string,
    maternalId: React.PropTypes.string,
    sex: React.PropTypes.string,
    affected: React.PropTypes.string,
    phenotips: React.PropTypes.string,
    caseReviewStatus: React.PropTypes.string,
}


export default Individual
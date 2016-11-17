import React from 'react'
import {Grid, Icon} from 'semantic-ui-react'

import Modal from '../../../shared/components/Modal'


let CaseReviewStatusSelector = ({initialState}) =>
    <select value={initialState} name="case_review_status">
        <option value="">---</option>
        <option value="I">In Review</option>
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

        this.state = {
            showPhenotipsPDFModal: false
        }

        this.showPhenotipsPDFModal = this.showPhenotipsPDFModal.bind(this);
        this.hidePhenotipsPDFModal = this.hidePhenotipsPDFModal.bind(this);
    }

    showPhenotipsPDFModal() {
        this.setState({showPhenotipsPDFModal: true})
    }

    hidePhenotipsPDFModal() {
        this.setState({showPhenotipsPDFModal: false})
    }

    render() {
        const {
            project,
            family,
            individual_id,
            paternal_id,
            maternal_id,
            sex,
            affected,
            phenotips,
            case_review_status,
            phenotips_id
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
                    [<a onClick={this.showPhenotipsPDFModal} style={{cursor:"pointer"}}>PDF</a>]
                    {
                        this.state.showPhenotipsPDFModal ?
                            <Modal title={individual_id} onClose={this.hidePhenotipsPDFModal} size="large">
                                <iframe frameBorder={0}
                                        width="100%"
                                        height="100%"
                                        src={"/api/phenotips/proxy/view/"+phenotips_id+"?project="+project.project_id}
                                />
                            </Modal>
                            : null
                    }
                    {phenotips ? phenotips : null}

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
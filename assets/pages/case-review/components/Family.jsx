
import React from 'react'
import {Grid, Icon} from 'semantic-ui-react'

import Modal from '../../../shared/components/Modal'

class Family extends React.Component {

    constructor(props) {
        super(props)

        this.state = {
            showZoomedInPedigreeModal: false
        }


        this.showZoomedInPedigreeModal = this.showZoomedInPedigreeModal.bind(this);
        this.hideZoomedInPedigreeModal = this.hideZoomedInPedigreeModal.bind(this);
    }

    showZoomedInPedigreeModal() {
        this.setState({showZoomedInPedigreeModal: true})
    }

    hideZoomedInPedigreeModal() {
        this.setState({showZoomedInPedigreeModal: false})
    }


    render() {
        const {
            project_id,
            family_id,
            about_family_content,
            analysis_summary_content,
            causal_inheritance_mode,
            family_name,
            pedigree_image,
            short_description,
            internal_case_review_notes,
            internal_case_review_summary
        } = this.props;

        return <Grid style={{width: "100%"}}>
            <Grid.Row style={{paddingTop: "20px", paddingRight: "10px"}}>
                <Grid.Column width={3}>
                    <span style={{paddingLeft:"0px"}}>
                        <b>
                            Family: <span style={{margin: "3px"}}></span>
                            <a href={"/project/" + project_id + "/family/" + family_id}>{family_id}</a>
                        </b><br/>
                    </span><br/>
                    {pedigree_image ? (
                        <div>
                            <img src={pedigree_image}
                                 onClick={this.showZoomedInPedigreeModal}
                                 height="80px"
                                 style={{verticalAlign: "top", cursor:"zoom-in"}}
                            />
                            <br/>
                            {
                                this.state.showZoomedInPedigreeModal ?
                                    <Modal title={"Family " +family_id} onClose={this.hideZoomedInPedigreeModal}>
                                        <img src={pedigree_image} style={{maxHeight: "250px", maxWidth: "400px"}}/>
                                    </Modal>
                                    : null
                            }
                        </div>) : null
                    }
                </Grid.Column>

                <Grid.Column width={13}>
                    {short_description ? <div>Short Description: {short_description}<br/></div> : null}
                    {about_family_content ? <div>Family Notes: {about_family_content}<br/></div> : null}
                    {analysis_summary_content ?
                        <div><b>Analysis Summary:</b> {analysis_summary_content}<br/></div> : null}

                    Internal Notes: &nbsp;
                    {internal_case_review_notes ? {internal_case_review_notes} : " -- "}
                    &nbsp;
                    <a href=""> <Icon link name="write"/></a>
                    <br/>

                    Internal Summary: &nbsp; {internal_case_review_summary ? {internal_case_review_summary} : " -- "}
                    &nbsp;
                    <a href=""> <Icon link name="write"/></a>
                    <br/>

                </Grid.Column>

            </Grid.Row>
        </Grid>

    }

}


export default Family

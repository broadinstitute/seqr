/* eslint no-undef: "warn" */

import React from 'react'
import { connect } from 'react-redux'
import { bindActionCreators } from 'redux'
import Checkbox from '../../../shared/components/form/Checkbox'
import Modal from '../../../shared/components/Modal'

//import { startSearch, cancelSearch } from '../actions/searchStatus'
//import { getSearchParams } from '../reducers/rootReducer'
//import { getSearchInProgressId, getSearchErrorMessage } from '../reducers/searchStatus'

// define presentational component
//const SearchButton = ({searchInProgress, startSearch, searchParams}) =>
//    <input type="button" value="Search" onClick={ () => startSearch(searchParams) } disabled={ searchInProgress } />



// wrap presentational components in a container
const mapStateToProps = (state) => state //({
    /**
    searchParams: getSearchParams(state),
    searchInProgress: getSearchInProgressId(state),
    errorMessage: getSearchErrorMessage(state)
     */
//});


let CaseReviewStatusSelector = ({
    initialState
}) => {
    return <select value={initialState} name="case_review_status">
        <option value="">---</option>
        <option value="A">Accepted</option>
        <option value="E">Accepted: Exome</option>
        <option value="G">Accepted: Genome</option>
        <option value="R">Not Accepted</option>
        <option value="N">See Notes</option>
        <option value="H">Hold</option>
    </select>
}

let Family = ({
    project_id,
    family_id,
    about_family_content,
    analysis_summary_content,
    causal_inheritance_mode,
    family_name,
    pedigree_image,
    short_description,
    internal_case_review_notes="",
    internal_case_review_summary=""
}) => <div>

    <div className="ui grid" style={{width:"100%"}}>
        <div className="row" style={{paddingTop:"20px", paddingRight: "10px"}}>
            <div className="three wide column">
                {pedigree_image ?
                    <div>
                        <img src={pedigree_image} height="80px" style={{verticalAlign:"top"}}/>
                        <Modal>
                            <img src={pedigree_image} style={{maxHeight:"250px", maxWidth:"400px"}}/>
                        </Modal>

                        <a style={{padding: "7px"}} onClick={(event)=>{  }} styl={{verticalAlign:"top"}}>
                            <i className="fa fa-search-plus"></i>
                        </a>
                    </div>: null
                }
            </div>
            <div className="seven wide column">
                {short_description ? <div><b>Short Description:</b> {short_description}<br/></div> : null}
                {about_family_content ? <div><b>Family Notes:</b> {about_family_content}<br/></div> : null}
                {analysis_summary_content ? <div><b>Analysis Summary:</b> {analysis_summary_content}<br/></div> : null}

                <b>Internal Notes: &nbsp; </b>
                {internal_case_review_notes ? {internal_case_review_notes} : " -- "}
                &nbsp;
                <a href=""> <i className={"fa fa-pencil"}></i></a>
                <br/>

                <b>Internal Summary: &nbsp; </b>{internal_case_review_summary ? {internal_case_review_summary} : " -- "}
                &nbsp;
                <a href=""> <i className={"fa fa-pencil"}></i></a>
                <br/>

            </div>
            <div className="six wide column">
                <span style={{position:"absolute", right:0}}>
                    Family: <span style={{margin:"3px"}}></span>
                    <b><a href={"/project/"+project_id+"/family/"+family_id}>{family_id}</a></b><br/>
                </span>

            </div>
        </div>
    </div>

</div>




//const mapDispatchToProps = (dispatch) => bindActionCreators({startSearch, cancelSearch},  dispatch)

let Individual = ({
    family,
    individual_id,
    paternal_id,
    maternal_id,
    sex,
    affected,
    phenotips = null,
    case_review_status,
    in_case_review,
}) => {
    return <div>
        <div className="ui grid" style={{width: "100%"}}>
            <div className="row" style={{paddingTop: "15px"}}>
                <div className="ten wide column" style={{padding:"10px"}}>
                    <div style={{position:"absolute", bottom:5, left:0}}>
                        <b><i style={{fontSize: "12px"}} className={
                            "fa fa-" + (
                                (sex == 'U' || affected == 'U') ? 'question-circle-o' : (
                                (sex == 'M' ? 'square' : 'circle') + (affected == 'N' ? '-o' : ''))
                            )}> </i></b>

                        <span style={{margin: "10px"}} />

                        {individual_id}
                        {
                            (!family.pedigree_image && (paternal_id || maternal_id)) ? (
                                <div style={{fontSize: "8pt"}}>
                                    child of &nbsp;
                                    <i>{(paternal_id && maternal_id) ? paternal_id + ", "+ maternal_id : (paternal_id || maternal_id)}</i>
                                </div>) : null
                        }

                        <span style={{margin: "10px"}} />

                        PhenoTips: { phenotips? "" : " -- "}
                        [<a href="google.com">PDF</a>]
                    </div>
                </div>
                <div className="six wide column">
                    <div style={{position:"absolute", bottom:5, right:0}}>
                        <span style={{paddingRight: "25px"}}>
                            <CaseReviewStatusSelector initialState={case_review_status}/>
                        </span>
                        <span style={{paddingRight: "5px"}}>In Review?
                            <Checkbox initialState={in_case_review} onClick={ () => {
                            } } style={{marginLeft: '15px'}}/>
                        </span>
                    </div>
                </div>
            </div>
        </div>
    </div>
}




let FamiliesAndIndividuals = ({
    project,
    families_by_id,
    individuals_by_id,
    family_id_to_indiv_ids
}) => <div>
    <table className='ui celled table' style={{width:"100%"}}>
        <tbody>
        {
            Object.keys(families_by_id).map((family_id, family_i) => {

                return <tr key={family_id} style={{backgroundColor: family_i % 2 == 0 ? 'white' : '#F3F3F3'}}>
                    <td style={{padding:"5px 0px 15px 15px"}}>
                        <Family project_id={project.project_id} family_id={family_id} {...families_by_id[family_id]} />

                        <table className='ui celled table' style={{
                            width:'100%',
                            margin:'0px',
                            backgroundColor:'transparent',
                            borderWidth:'0px'}}> <thead/> <tbody>
                        {
                            family_id_to_indiv_ids[family_id].map((individual_id, individual_i) => {
                                return <tr key={individual_i}>
                                    <td style={{padding:"10px 0px 0px 15px", borderWidth:"0px"}}>
                                        <Individual
                                            family={families_by_id[family_id]}
                                            {... individuals_by_id[individual_id]} />
                                    </td>
                                </tr>
                            })
                        }
                        </tbody>
                        </table>
                    </td>
                </tr>

            })
        }
        </tbody>
    </table>
</div>



FamiliesAndIndividuals = connect(mapStateToProps)(FamiliesAndIndividuals)

export default FamiliesAndIndividuals

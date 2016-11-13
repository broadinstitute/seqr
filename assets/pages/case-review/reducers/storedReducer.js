
export const SET_IS_INDIVIDUAL_IN_CASE_REVIEW = "SET_IS_INDIVIDUAL_IN_CASE_REVIEW"


//action creators
export const setIsIndividualInCaseReview = (indivId, isInCaseReview) => ({
    'type': SET_IS_INDIVIDUAL_IN_CASE_REVIEW,
    'indiv_id': indivId,
    'in_case_review': isInCaseReview,
})


const storedReducer = (state = {
    'user': {},
    'project': {},
    'family_id_to_indiv_ids': {},
    'families_by_id': {},
    'individuals_by_id': {},
}, action) => {
    return state;
}


export default storedReducer;


// selectors
export const getUser = (state) => state.stored.user
export const getProject = (state) => state.stored.project
export const getFamilyIdToIndividualIds = (state) => state.stored.family_id_to_indiv_ids
export const getFamiliesById = (state) => state.stored.families_by_id
export const getIndividualsById = (state) => state.stored.individuals_by_id


export const getFamilyState = (state, familyId) => state.stored.individuals_by_id[familyId]
export const getIndividualState = (state, indivId) => state.stored.individuals_by_id[indivId]

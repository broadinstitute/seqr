import { combineReducers } from 'redux';
import { inheritanceModes } from './select-inheritance-modes'

const selectedIndividuals = (state = {
    allow_multiple_project_selection: false,
    allow_multiple_family_selection: false,
    selected_project_group_ids: [],
    selected_project_ids: [],
    selected_family_ids: [],
}, action) => {
    return state
}


const loci = (state = {
    selected_gene_list_ids: [],
    gene_ids: [],
    ranges: [],
    ranges_permit_partial_overlap: true,
}, action) => {
    return state
}

const consequences = (state = {
    frameshift: true,
    start_gain: true,
    stop_gain: true,
}, action) => {
    return state
}

const alleleFrequencies = (state = {
    /*
    internal_to_callset: 0.01,
    exac_v2: 0.01,
    exac_afr_v2: 0.01,
    exac_v2_popmax: 0.01,
    g1k_wgs_phase3: 0.01,
    g1k_wgs_phase3_popmax: 0.01,
    */
}, action) => {
    return state
}

const variantQC = (state = {
    pass_only: true,
}, action) => {
    return state
}

const genotypeQC = (state = {
    affected_gq: 20,
    affected_dp: 20,
    affected_ab: 0.5
}, action) => {
    return state
}

const clinical = (state = {
    //in_clinvar: true | false
    //in_omim: true | false
}, action) => {
    return state
}

const resultsFormat = (state = {
    /*
    group_by: variant | family
    sort_by: {
        position: true,
        allele_frequency: false,
    }

    page:
    num_variants_per_page:
    */
}, action) => {
    return state
}

const searchParameters = combineReducers({
    selectedIndividuals,
    inheritanceModes,
    loci,
    consequences,
    alleleFrequencies,
    variantQC,
    genotypeQC,
    clinical,
    resultsFormat,

})

const searchState = (state = {
    inProgress: false,
    errorMessage: null,
    failed: false,
    succeeded: false,
}, action) => {
    return state
};

const searchResults = (state = {
    variants: []
}, action) => {
    return state
};

export const rootReducer = combineReducers({
    searchParameters,
    searchState,
    searchResults,
});


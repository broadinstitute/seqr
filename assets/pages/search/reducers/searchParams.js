import { combineReducers } from 'redux'

import inheritanceModes from './search-params/inheritanceModes'

const selectedIndividuals = (state = {
    allowMultipleProjectSelection: false,
    allowMultipleFamilySelection: false,
    selectedProjectGroupIds: [],
    selectedProjectIds: [],
    selectedFamilyIds: [],
}, action) => {
    return state
}


const loci = (state = {
    selectedGeneListIds: [],
    geneIds: [],
    ranges: [],
    rangesPermitPartialOverlap: true,
}, action) => {
    return state
}

const consequences = (state = {
    frameshift: true,
    startGain: true,
    stopGain: true,
}, action) => {
    return state
}

const alleleFrequencies = (state = {
    /*
     internalToCallset: 0.01,
     exac2: 0.01,
     exac2Afr: 0.01,
     exacV2Popmax: 0.01,
     g1KWgsPhase3: 0.01,
     g1KWgsPhase3Popmax: 0.01,
     */
}, action) => {
    return state
}

const variantQC = (state = {
    passOnly: true,
}, action) => {
    return state
}

const genotypeQC = (state = {
    affectedGQ: 20,
    affectedDP: 20,
    affectedAB: 0.5
}, action) => {
    return state
}

const clinical = (state = {
    //inClinvar: true | false
    //inOmim: true | false
}, action) => {
    return state
}

const resultsFormat = (state = {
    /*
     groupBy: variant | family
     sortBy: {
     position: true,
     alleleFrequency: false,
     }

     page:
     numVariantsPerPage:
     */
}, action) => {
    return state
}

const searchParams = combineReducers({
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

export default searchParams;


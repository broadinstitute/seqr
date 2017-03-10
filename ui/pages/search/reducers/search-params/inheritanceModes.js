
//actions
const TOGGLE_HOMOZYGOUS_RECESSIVE = 'TOGGLE_HOMOZYGOUS_RECESSIVE';
const TOGGLE_COMPOUND_HET = 'TOGGLE_COMPOUND_HET';
const TOGGLE_XLINKED_RECESSIVE = 'TOGGLE_XLINKED_RECESSIVE';
const TOGGLE_DOMINANT = 'TOGGLE_DOMINANT';
const TOGGLE_DE_NOVO = 'TOGGLE_DE_NOVO';


//action creators
export const toggleInheritanceModeActionCreators = {
    toggleHomozygousRecessive: (toValue) => ({type: TOGGLE_HOMOZYGOUS_RECESSIVE, toValue}),
    toggleCompoundHet: (toValue) => ({type: TOGGLE_COMPOUND_HET, toValue}),
    toggleXLinkedRecessive: (toValue) => ({type: TOGGLE_XLINKED_RECESSIVE, toValue}),
    toggleDominant: (toValue) => ({type: TOGGLE_DOMINANT, toValue}),
    toggleDeNovo: (toValue) => ({type: TOGGLE_DE_NOVO, toValue}),
}


//reducer
export default function inheritanceModes(state = {
    homozygousRecessive: false,
    compoundHet: true,
    xLinkedRecessive: true,
    dominant: true,
    deNovo: true,
}, action) {
    //console.log("Processing action: ", action)
    switch (action.type) {
        case TOGGLE_HOMOZYGOUS_RECESSIVE:  return { ...state, homozygousRecessive: action.toValue === undefined ? !state.homozygousRecessive : action.toValue };
        case TOGGLE_COMPOUND_HET:          return { ...state, compoundHet:         action.toValue === undefined ? !state.compoundHet : action.toValue };
        case TOGGLE_XLINKED_RECESSIVE:     return { ...state, xLinkedRecessive:    action.toValue === undefined ? !state.xLinkedRecessive : action.toValue };
        case TOGGLE_DOMINANT:              return { ...state, dominant:            action.toValue === undefined ? !state.dominant : action.toValue };
        case TOGGLE_DE_NOVO:               return { ...state, deNovo:              action.toValue === undefined ? !state.deNovo : action.toValue };
        default:
            return state
    }
}
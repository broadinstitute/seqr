import React from 'react'
import { bindActionCreators } from 'redux'
import { connect } from 'react-redux'
import { toggleInheritanceModeActionCreators } from '../reducers/select-inheritance-modes'

// 3-state checkbox that can be checked, unchecked, or half-checked
let TriStateCheckbox = ({initialState, onChecked, onUnchecked, ...props}) => {
    return <input type="checkbox"
                  onClick = {
                    (event) => {
                        if (event.target.checked && onChecked !== undefined) {
                            onChecked(event)
                        } else if (!event.target.checked && onUnchecked !== undefined) {
                            onUnchecked(event)
                        }
                    }
                  }
                  ref = {
                    (self) => {
                       if (self) {  // when this component is unmounted, ref is called with self === undefined
                           self.indeterminate = (initialState === 1)
                           self.checked = (initialState === 2)
                       }
                    }
                  }
                  {...props}
    />
}

// regular 2-state checkbox
let Checkbox = ({initialState, onClick, ...props}) => {
    return <input type="checkbox" onClick = { onClick } ref = { (self) => { if(self) self.checked = initialState }} {...props} />
}


// define presentational component
let InheritanceModeSelector = ({selectorStates, boundActions}) => {
    return <div>
        <TriStateCheckbox
            initialState={ (() => {
                let nChildrenChecked = selectorStates.homozygousRecessive + selectorStates.compoundHet + selectorStates.xLinkedRecessive
                return nChildrenChecked == 0 ? 0 : (nChildrenChecked < 3 ? 1 : 2) })()
            }
            onChecked={ () => {
                boundActions.toggleHomozygousRecessive(true)
                boundActions.toggleCompoundHet(true)
                boundActions.toggleXLinkedRecessive(true)
            }}
            onUnchecked={ () => {
                boundActions.toggleHomozygousRecessive(false)
                boundActions.toggleCompoundHet(false)
                boundActions.toggleXLinkedRecessive(false)
            }}
        /> Recessive:<br/>
        <Checkbox initialState={selectorStates.homozygousRecessive} onClick={ () => boundActions.toggleHomozygousRecessive() } style={{marginLeft: '30px'}}/> Homozygous
        <span width="10px" /><Checkbox initialState={selectorStates.compoundHet}         onClick={ () => boundActions.toggleCompoundHet() }  style={{marginLeft: '10px'}} />         Compound Het
        <span width="10px" /><Checkbox initialState={selectorStates.xLinkedRecessive}    onClick={ () => boundActions.toggleXLinkedRecessive() }  style={{marginLeft: '10px'}} />    X-Linked
        <br />
        <TriStateCheckbox
            initialState={ (() => {
                let nChildrenChecked = selectorStates.dominant + selectorStates.deNovo
                return nChildrenChecked == 0 ? 0 : (nChildrenChecked < 2 ? 1 : 2) })()
            }
            onChecked={ () => {
                boundActions.toggleDominant(true)
                boundActions.toggleDeNovo(true)
            }}
            onUnchecked={ () => {
                boundActions.toggleDominant(false)
                boundActions.toggleDeNovo(false)
            }}
        /> Dominant:<br/>
            <Checkbox initialState={ selectorStates.dominant } onClick={ () => boundActions.toggleDominant() }  style={{marginLeft: '30px'}}/>  Dominant
            <Checkbox initialState={ selectorStates.deNovo }   onClick={ () => boundActions.toggleDeNovo() }  style={{marginLeft: '10px'}}/>    De Novo
    </div>
}

const mapStateToProps = (state) => {
    return {selectorStates: state.searchParameters.inheritanceModes }
};

const mapDispatchToProps = (dispatch) => {
    return {boundActions: bindActionCreators(toggleInheritanceModeActionCreators,  dispatch)}
};

// wrap in container
InheritanceModeSelector = connect(mapStateToProps, mapDispatchToProps)(InheritanceModeSelector);

export { InheritanceModeSelector }

import React from 'react'
import { bindActionCreators } from 'redux'
import { connect } from 'react-redux'
import { toggleInheritanceModeActionCreators } from '../reducers/search-params/inheritanceModes'
import Checkbox from '../../../shared/components/form/Checkbox'

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



// define presentational component
let InheritanceModeFilters = ({selectorStates, boundActions}) => {
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
        /> <b>Recessive:</b><br/>
        <Checkbox initialState={selectorStates.homozygousRecessive} onClick={ () => boundActions.toggleHomozygousRecessive() } style={{marginLeft: '15px'}}/>  Homozygous <br />
        <Checkbox initialState={selectorStates.compoundHet}         onClick={ () => boundActions.toggleCompoundHet() }  style={{marginLeft: '15px'}} />  Compound Het <br/>
        <Checkbox initialState={selectorStates.xLinkedRecessive}    onClick={ () => boundActions.toggleXLinkedRecessive() }  style={{marginLeft: '15px'}} />  X-Linked <br/>
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
        /> <b>Dominant:</b><br/>
        <Checkbox initialState={ selectorStates.dominant } onClick={ () => boundActions.toggleDominant() }  style={{marginLeft: '15px'}}/>  Dominant <br />
        <Checkbox initialState={ selectorStates.deNovo }   onClick={ () => boundActions.toggleDeNovo() }  style={{marginLeft: '15px'}}/>    De Novo  <br />
    </div>
}

const mapStateToProps = (state) => {
    return {selectorStates: state.searchParams.inheritanceModes }
};

const mapDispatchToProps = (dispatch) => {
    return {boundActions: bindActionCreators(toggleInheritanceModeActionCreators,  dispatch)}
};

// wrap in container
InheritanceModeFilters = connect(mapStateToProps, mapDispatchToProps)(InheritanceModeFilters);

export default InheritanceModeFilters

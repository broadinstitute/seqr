/* eslint-disable prefer-rest-params */
/* eslint-disable no-unused-vars */

/* partly based on https://www.npmjs.com/package/react-log-lifecycle */

import React from 'react'

/***********************
 *  constants
 ***********************/


const ALL_LIFECYCLE_METHODS = new Set([
  'componentWillMount',
  'componentDidMount',
  'render',
  'componentWillUnmount',
  'componentWillReceiveProps',
  'shouldComponentUpdate',
  'componentWillUpdate',
  'componentDidUpdate',
  'componentWillUnmount',
])

const VALID_METHOD_NAMES = new Set([
  ...ALL_LIFECYCLE_METHODS,
  'createElement',
  'constructor',
])


/***********************
 *  utility functions
 ***********************/

const validateLifecycleMethodNames = (methodNames) => {
  methodNames
    .filter(methodName => !VALID_METHOD_NAMES.has(methodName))
    .forEach(invalidMethodName => console.warn('Invalid lifecycle method name: ', invalidMethodName))

}

const arrayMinusSet = (a, b) => [...a].filter(x => !b.has(x))


//log message format
const message = (componentType, methodName, props) => {
  const args = props ?
    Object.entries(props)
      .filter(([k, v]) => (v && typeof v !== 'function' && typeof v !== 'object'))
      .map(([k, v]) => `${k}='${v}'`)
      .join(', ')
    : ''
  return `${componentType.displayName || componentType.name || componentType}.${methodName}(${args})`
}

const lifecycleFunctionWrapperFactory = (originalMethod, componentName, lifecycleMethodName, props, showTimingInfo = true) => {
  const consoleLogStart = showTimingInfo ? console.time : console.log
  const consoleLogEnd = showTimingInfo ? console.timeEnd : () => {}

  return function () {
    const m = message(componentName, lifecycleMethodName, props)
    consoleLogStart(m)
    const methodResult = originalMethod.apply(this, arguments)
    consoleLogEnd(m)
    return methodResult
  }
}


/************************************
 *  patchReactToLogLifecycleMethods
 ************************************/


export const patchReactToLogLifecycleMethods = ({
  includeTypes = [], // arg definition based on: http://2ality.com/2011/11/keyword-parameters.html
  excludeTypes = [],
  includeMethods = [
    'createElement',
    ...ALL_LIFECYCLE_METHODS,
  ],
  excludeMethods = [],
  showTimingInfo = false,
} = {}) => {

  //validate args
  validateLifecycleMethodNames(includeMethods)
  validateLifecycleMethodNames(excludeMethods)

  // decide which methods to instrument
  const includeTypesSet = new Set(includeTypes)
  const excludeTypesSet = new Set(excludeTypes)

  const includeMethodsSet = new Set(includeMethods)
  const exludeMethodsSet = new Set(excludeMethods)

  const instrumentCreateElement = includeMethodsSet.has('createElement') && !exludeMethodsSet.has('createElement')
  const originalCreateElement = React.createElement

  const lifecycleMethodsToInstrument = arrayMinusSet(includeMethods.filter(x => x !== 'createElement'), exludeMethodsSet)

  const consoleLogStart = showTimingInfo ? console.time : console.log
  const consoleLogEnd = showTimingInfo ? console.timeEnd : () => {}

  // monkey patch createElement
  React.createElement = function (type, props) {
    const typeName = type.displayName || type.name || type
    if ((includeTypes.length > 0 && !includeTypesSet.has(typeName)) || excludeTypesSet.has(typeName)) {
      return originalCreateElement.apply(this, arguments)
    }

    let element
    if (instrumentCreateElement) {
      const m = message(typeName, 'createElement', props)
      consoleLogStart(m)
      element = originalCreateElement.apply(this, arguments)
      consoleLogEnd(m)
    } else {
      element = originalCreateElement.apply(this, arguments)
    }

    // monkey patch lifecycle methods in the newly-created element
    if (lifecycleMethodsToInstrument.length > 0 && element.type.prototype) {
      lifecycleMethodsToInstrument.forEach((lifecycleMethodName) => {
        if (element.type.prototype[lifecycleMethodName]) {
          const originalMethod = element.type.prototype[lifecycleMethodName]
          element.type.prototype[lifecycleMethodName] = lifecycleFunctionWrapperFactory(originalMethod, typeName, lifecycleMethodName, props, showTimingInfo)
        }
      })
    }

    return element
  }
}


/************************
 *  logLifecycleMethods
 ************************/


export const logLifecycleMethods = (
  WrappedComponent, // arg definition based on: http://2ality.com/2011/11/keyword-parameters.html
  {
    includeMethods = [
      'constructor',
      'componentWillMount',
      'componentDidMount',
      'render',
      'componentWillUnmount',
      'componentWillReceiveProps',
      'shouldComponentUpdate',
      'componentWillUpdate',
      'componentDidUpdate',
      'componentWillUnmount',
    ],
    excludeMethods = [],
    showTimingInfo = true,
  } = {},
) => {

  //validate args
  validateLifecycleMethodNames(includeMethods)
  validateLifecycleMethodNames(excludeMethods)

  const includeMethodsSet = new Set(includeMethods)
  const exludeMethodsSet = new Set(excludeMethods)

  const instrumentConstructor = includeMethodsSet.has('constructor') && !exludeMethodsSet.has('constructor')
  const instrumentRender = includeMethodsSet.has('render') && !exludeMethodsSet.has('render')
  const lifecycleMethodsToInstrument = arrayMinusSet(includeMethods.filter(x => (x !== 'constructor' && x !== 'render')), exludeMethodsSet)

  const consoleLogStart = showTimingInfo ? console.time : console.log
  const consoleLogEnd = showTimingInfo ? console.timeEnd : () => {}

  return class extends React.Component {

    constructor(props) {
      if (instrumentConstructor) {
        const m = message(WrappedComponent, 'constructor', props)
        consoleLogStart(m)
        super(props)
        consoleLogEnd(m)
      } else {
        super(props)
      }

      this.render = () => {
        if (instrumentRender) {
          const m = message(WrappedComponent, 'render', this.props)
          consoleLogStart(m)
          const component = <WrappedComponent {...this.props} />
          consoleLogEnd(m)

          return component
        }

        return <WrappedComponent {...this.props} />
      }

      lifecycleMethodsToInstrument.forEach((methodName) => {
        if (super[methodName]) {
          const originalMethod = super[methodName]
          this[methodName] = lifecycleFunctionWrapperFactory(originalMethod, WrappedComponent, methodName)
        }
      })

      //TODO create a more complete proxy - http://exploringjs.com/es6/ch_proxies.html
    }
  }
}


// Utility functions for Semantic UI

export const optionsAreEqual = (options, nextOptions) => {
  if (nextOptions) {
    if (nextOptions.length !== (options || []).length) {
      return false
    }
    if (Object.entries(nextOptions)
      .some(([i, opt]) => ['value', 'text', 'color', 'disabled', 'description']
        .some(k => opt[k] !== options[i][k]))
    ) {
      return false
    }
  }
  return true
}

export const propsAreEqual = (props, nextProps) => {
  if (!optionsAreEqual(props.options, nextProps.options)) {
    return false
  }
  if (Object.keys(nextProps).filter(k => k !== 'onChange' && k !== 'options').some(
    k => nextProps[k] !== props[k],
  )) {
    return false
  }
  return true
}

export const semanticShouldUpdate = (that, nextProps, nextState) => {
  if (!propsAreEqual(that.props, nextProps)) {
    return true
  }
  return nextState !== that.state
}

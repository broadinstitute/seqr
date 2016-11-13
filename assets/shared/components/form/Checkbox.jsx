import React from 'react';

// regular 2-state checkbox
let Checkbox = ({initialState, onClick, ...props}) => {
    return <input type="checkbox" onClick = { onClick } checked= { initialState == 1 ? "checked" : null } {...props} />
}

export default Checkbox;
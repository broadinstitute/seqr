import React from 'react';

// regular 2-state checkbox
let Checkbox = ({initialState, onClick, ...props}) => {
    return <input type="checkbox" onClick = { onClick } ref = { (self) => { if(self) self.checked = initialState }} {...props} />
}

export default Checkbox;
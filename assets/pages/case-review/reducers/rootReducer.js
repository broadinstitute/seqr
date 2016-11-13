import { combineReducers } from 'redux'

import storedReducer from './storedReducer';
import otherReducer from './otherReducer';

// reducer
const rootReducer = combineReducers({
    'stored': storedReducer,
    'other': otherReducer,
});

export default rootReducer;


//utilities to save and restore in the client-side local store.


export const saveState = (label, state) => {
    try {
        const serializedState = JSON.stringify(state);
        localStorage.setItem(label, serializedState);
    } catch (err) {
        // Ignore write errors.
    }
};


export const loadState = (label) => {
    try {
        const serializedState = localStorage.getItem(label);
        if (serializedState === null) {
            return undefined;
        }
        return JSON.parse(serializedState);
    } catch (err) {
        return undefined;
    }
};

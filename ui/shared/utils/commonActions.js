

const UPDATE_PROJECT = 'UPDATE_PROJECT'

//when it's a page with a single project
export const updateProject = project => ({ type: UPDATE_PROJECT, updates: project })

/**
TODO have common reducers for different state shapes (depending on whether the page has
 1 or multiple projects,
 1 or multiple families,
 1 or multiple indivudals,
 etc.
 */

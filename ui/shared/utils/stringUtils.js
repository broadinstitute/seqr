export const snakecaseToTitlecase = s => (s || '').split('_').map(word => word[0].toUpperCase() + word.slice(1)).join(' ')

export const toSnakecase = s => (s || '').replace(/ /g, '_').toLowerCase()

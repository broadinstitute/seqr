export const titlecase = s => s.split('_').map(word => word[0].toUpperCase() + word.slice(1)).join(' ')

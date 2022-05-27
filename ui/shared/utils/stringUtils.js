const removeMd = require('@tommoor/remove-markdown')

export const snakecaseToTitlecase =
  s => (s ? s.split('_').map(word => word[0].toUpperCase() + word.slice(1)).join(' ') : '')

export const camelcaseToTitlecase = s => (s ? s[0].toUpperCase() + s.slice(1).replace(/([A-Z]+)/g, ' $1') : '')

export const toSnakecase = s => (s || '').replace(/ /g, '_').toLowerCase()

export const toCamelcase = s => (s || '').split(' ').map(
  (word, i) => word && (i > 0 ? word[0].toUpperCase() : word[0].toLowerCase()) + word.slice(1),
).join('')

export const stripMarkdown = s => removeMd((s || '').replace(/\n/g, ' '))

export const toUniqueCsvString = (...csvStrs) => {
  const concated = ''.concat(csvStrs)
  const splitted = concated.split(',').filter(s => s).map(s => s.trim())

  return [...new Set(splitted)].join(',')
}

export const sizeToBytes = (string) => {
  if (!string || string.length < 2) return null

  const units = {
    kb: 1024,
    mb: 1024 * 1024,
    gb: 1024 * 1024 * 1024,
    tb: 1024 * 1024 * 1024 * 1024,
    pb: 1024 * 1024 * 1024 * 1024 * 1024,
    eb: 1024 * 1024 * 1024 * 1024 * 1024 * 1024,
  }
  const size = parseFloat(string.slice(0, -2))
  const stringUnit = string.slice(-2).toLowerCase()

  return size * units[stringUnit]
}

export const formatBytes = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  if (!bytes) return null
  const k = 1024
  const dm = 2
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${parseFloat((bytes / (k ** i)).toFixed(dm))}\xa0${sizes[i]}`
}

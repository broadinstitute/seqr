import Timeago from 'timeago.js'

/**
 * Returns a string that concatenates the label with the date in a nicer format.
 * @param label String label to put in from the date.
 * @param dateString
 * @param upperCase
 */
export const formatDate = (label, dateString, upperCase = true) => {
  if (dateString) {
    const s = `${label} ${new Timeago().format(dateString)}`
    if (upperCase) {
      return s.toUpperCase()
    }
    return s
  }

  return null
}

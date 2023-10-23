import removeMd from '@tommoor/remove-markdown'

/**
 * Converts a snake_case string to title case.
 *
 * @param {string} s - The snake_case string to convert.
 * @returns {string} The title case string.
 *
 * @example
 * const titleCase = snakecaseToTitlecase('hello_world_example');
 * // Returns: 'Hello World Example'
 */
export const snakecaseToTitlecase =
  (s: string): string => (s ? s.split('_').map(word => word[0].toUpperCase() + word.slice(1)).join(' ') : '')

/**
 * Converts a camelCase string to title case.
 *
 * @param {string} s - The camelCase string to convert.
 * @returns {string} The title case string.
 *
 * @example
 * const titleCase = camelcaseToTitlecase('helloWorldExample');
 * // Returns: 'Hello World Example'
 */
export const camelcaseToTitlecase = (s: string): string => (s ? s[0].toUpperCase() + s.slice(1).replace(/([A-Z]+)/g, ' $1') : '')

/**
 * Converts a string to snake_case.
 *
 * @param {string} s - The string to convert.
 * @returns {string} The snake_case string.
 *
 * @example
 * const snakeCase = toSnakecase('Hello World Example');
 * // Returns: 'hello_world_example'
 */
export const toSnakecase = (s: string): string => (s || '').replace(/ /g, '_').toLowerCase()

/**
 * Converts a string to camelCase.
 *
 * @param {string} s - The string to convert.
 * @returns {string} The camelCase string.
 *
 * @example
 * const camelCase = toCamelcase('hello world example');
 * // Returns: 'helloWorldExample'
 */
export const toCamelcase = (s: string): string => (s || '').split(' ').map(
  (word, i) => word && (i > 0 ? word[0].toUpperCase() : word[0].toLowerCase()) + word.slice(1),
).join('')

/**
 * Removes Markdown formatting and converts newline characters to spaces.
 *
 * @param {string} s - The input string containing Markdown-formatted text.
 * @returns {string} The text with Markdown formatting removed and newlines replaced by spaces.
 *
 * @example
 * const plainText = stripMarkdown('# Hello\n**World**');
 * // Returns: 'Hello World'
 */
export const stripMarkdown = (s: string): string => removeMd((s || '').replace(/\n/g, ' '))

/**
 * Concatenates and deduplicates an array of CSV strings, returning a unique CSV string.
 *
 * @param {...string} csvStrs - The CSV strings to concatenate and deduplicate.
 * @returns {string} A unique CSV string containing non-empty values separated by commas.
 *
 * @example
 * const uniqueCsv = toUniqueCsvString('str1,str2', 'str2,str3', 'str4,str5');
 * // Returns: 'str1,str2,str3,str4,str5'
 */
export const toUniqueCsvString = (...csvStrs: string[]) => {
  const concated = csvStrs.join(',').trim()
  const splitted = concated.split(',').filter(s => s).map(s => s.trim())

  return [...new Set(splitted)].join(',')
}

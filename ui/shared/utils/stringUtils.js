import React from 'react'
import ReactDOMServer from 'react-dom/server'
import MarkdownRenderer from 'react-markdown-renderer'

export const snakecaseToTitlecase = s =>
  (s ? s.split('_').map(word => word[0].toUpperCase() + word.slice(1)).join(' ') : '')

export const camelcaseToTitlecase = s =>
  (s ? s[0].toUpperCase() + s.slice(1).replace(/([A-Z]+)/g, ' $1') : '')

export const toSnakecase = s => (s || '').replace(/ /g, '_').toLowerCase()

export const toCamelcase = s => (s || '').split(' ').map(
  (word, i) => word && (i > 0 ? word[0].toUpperCase() : word[0].toLowerCase()) + word.slice(1),
).join('')

export const stripMarkdown = s =>
  ReactDOMServer.renderToStaticMarkup(<MarkdownRenderer markdown={s || ''} />).replace(/(<([^>]+)>)/ig, '').trim()

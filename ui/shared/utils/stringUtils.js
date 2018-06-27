import React from 'react'
import ReactDOMServer from 'react-dom/server'
import MarkdownRenderer from 'react-markdown-renderer'

export const snakecaseToTitlecase = s => (s || '').split('_').map(word => word[0].toUpperCase() + word.slice(1)).join(' ')

export const toSnakecase = s => (s || '').replace(/ /g, '_').toLowerCase()

export const stripMarkdown = s =>
  ReactDOMServer.renderToStaticMarkup(<MarkdownRenderer markdown={s || ''} />).replace(/(<([^>]+)>)/ig, '')

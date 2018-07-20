import { snakecaseToTitlecase, toSnakecase, toCamelcase, stripMarkdown } from './stringUtils'

test('snakecaseToTitlecase', () => {
  expect(snakecaseToTitlecase('hello_world_foo')).toEqual('Hello World Foo')
  expect(snakecaseToTitlecase(null)).toEqual('')
})

test('toSnakecase', () => {
  expect(toSnakecase('Hello World foo')).toEqual('hello_world_foo')
  expect(toSnakecase(null)).toEqual('')
})

test('toCamelcase', () => {
  expect(toCamelcase('Hello World foo')).toEqual('helloWorldFoo')
  expect(toCamelcase(null)).toEqual('')
})

test('stripMarkdown', () => {
  expect(stripMarkdown('# Header: *emphasized text*')).toEqual('Header: emphasized text')
  expect(stripMarkdown(null)).toEqual('')
})

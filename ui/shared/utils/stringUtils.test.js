import { snakecaseToTitlecase, toSnakecase, toCamelcase, stripMarkdown } from './stringUtils'

test('snakecaseToTitlecase', () => {
  expect(snakecaseToTitlecase('hello_world_foo')).toEqual('Hello World Foo')
})

test('toSnakecase', () => {
  expect(toSnakecase('Hello World foo')).toEqual('hello_world_foo')
})

test('toCamelcase', () => {
  expect(toCamelcase('Hello World foo')).toEqual('helloWorldFoo')
})

test('stripMarkdown', () => {
  expect(stripMarkdown('# Header: *emphasized text*')).toEqual('Header: emphasized text')
})

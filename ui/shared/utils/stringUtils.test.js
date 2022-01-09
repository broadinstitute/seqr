import { snakecaseToTitlecase, toSnakecase, toCamelcase, stripMarkdown, toUniqueCsvString } from './stringUtils'

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
  expect(stripMarkdown('# Header:\n*emphasized\n\ntext*\n')).toEqual('Header: emphasized  text')
  expect(stripMarkdown(null)).toEqual('')
})

test('toUniqueCsvString', () => {
  expect(toUniqueCsvString('str1, str2', 'str2, str3', 'str3, str4')).toEqual('str1,str2,str3,str4')
  expect(toUniqueCsvString('str1,str2,', 'str3,str4')).toEqual('str1,str2,str3,str4')
  expect(toUniqueCsvString('', 'abc, def')).toEqual('abc,def')
  expect(toUniqueCsvString('')).toEqual('')
  expect(toUniqueCsvString('', '')).toEqual('')
  expect(toUniqueCsvString(null)).toEqual('')
  expect(toUniqueCsvString(undefined)).toEqual('')
})

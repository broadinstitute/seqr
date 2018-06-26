import { snakecaseToTitlecase } from './stringUtils'

test('genericComparator', () => {
  expect(snakecaseToTitlecase('hello_world_foo')).toEqual('Hello World Foo')
})

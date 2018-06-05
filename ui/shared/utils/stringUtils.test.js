import { titlecase } from './stringUtils'

test('genericComparator', () => {
  expect(titlecase('hello_world_foo')).toEqual('Hello World Foo')
})
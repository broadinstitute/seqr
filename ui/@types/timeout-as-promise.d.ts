declare module 'timeout-as-promise' {
  function delay(...args: unknown[]): Promise<unknown[]>

  export = delay
}

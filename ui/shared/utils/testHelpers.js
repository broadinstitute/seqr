// Test-only helpers for working with the global fetch() mock installed in
// config/jest/setupTests.js. Use these instead of mocking shared/utils/httpRequestHelper.js
// directly, so tests exercise the real HttpRequestHelper request/response handling.

// HttpRequestHelper.handlePromise chains several .then()s after fetch() resolves; awaiting a
// single microtask tick isn't always enough to let a dispatched action reach a mock store, so
// flush a few ticks. Call this (possibly more than once) after triggering a request and before
// asserting on dispatched actions or re-rendered UI.
export const flushPromises = () => new Promise(resolve => (typeof setImmediate === 'function' ? setImmediate(resolve) : setTimeout(resolve, 0)))

export const flushAll = async (times = 4) => {
  for (let i = 0; i < times; i += 1) {
    // eslint-disable-next-line no-await-in-loop
    await flushPromises()
  }
}

// Queue up the next fetch() call to resolve with the given JSON body.
export const mockFetchResponse = (json = {}, { ok = true, status = ok ? 200 : 400 } = {}) => {
  fetch.mockImplementationOnce(() => Promise.resolve({
    ok,
    status,
    json: () => Promise.resolve(json),
  }))
}

// Queue up the next fetch() call to reject outright (e.g. a network failure).
export const mockFetchRejection = (error = new Error('Network error')) => {
  fetch.mockImplementationOnce(() => Promise.reject(error))
}

// Convenience accessors for asserting on the most recent fetch() call.
export const getLastFetchUrl = () => fetch.mock.calls[fetch.mock.calls.length - 1]?.[0]

export const getLastFetchOptions = () => fetch.mock.calls[fetch.mock.calls.length - 1]?.[1]

export const getLastFetchBody = () => {
  const options = getLastFetchOptions()
  return options?.body ? JSON.parse(options.body) : undefined
}

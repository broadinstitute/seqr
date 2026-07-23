// Ensure tests never make a real network request: every test file gets a fresh mock of the
// global fetch() used by shared/utils/httpRequestHelper.js, defaulting to an empty successful
// JSON response. Individual tests can override this with fetch.mockImplementationOnce(...),
// fetch.mockResolvedValueOnce(...), or inspect calls via fetch.mock.calls.
beforeEach(() => {
  global.fetch = jest.fn(() => Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve({}),
  }))
})

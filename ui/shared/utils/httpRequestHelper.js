import Cookies from 'js-cookie'
import delay from 'timeout-as-promise'

export const getUrlQueryString = urlParams =>
  Object.entries(urlParams).map(([key, value]) => [key, value].map(encodeURIComponent).join('=')).join('&')

/**
 * Encapsulates the cycle of:
 * 1. sending an HTTP request to the server
 * 2. calling an onSuccess or onError handler with the response.
 * 3. setting a timer, and then clearing any notification message after a few seconds, assuming
 *    no new request was started.
 */
export class HttpRequestHelper {

  /**
   * Creates a new HttpPost helper.
   * @param url {string} The URL to send the request to.
   * @param onSuccess {function} optional handler called if server responds with status code 200
   * @param onError {function} optional handler called if server responds with a code other than 200
   * @param onClear {function} optional handler called some time after the onSuccess or onError handler is called
   * @param delayBeforeClearing {number} milliseconds delay before calling the onClear handler
   */
  constructor(url, onSuccess = null, onError = null, onClear = null, delayBeforeClearing = 3000, debug = false) {
    this.url = url
    this.httpPostId = 0
    this.onSuccess = onSuccess
    this.onError = onError
    this.onClear = onClear
    this.delayBeforeClearing = delayBeforeClearing
    this.debug = debug
  }

  /**
   * Submit an HTTP GET request.
   * @param urlParams A dictionary of key-value pairs {gene: 'ENSG00012345', chrom: '1'} to encode
   *   and append to the url as HTTP GET params (eg. "?gene=ENSG00012345&chrom=1")
   */
  get = (urlParams = {}) => {
    const urlQueryString = getUrlQueryString(urlParams)

    const p = fetch(`${this.url}?${urlQueryString}`, {
      method: 'GET',
      credentials: 'include',
    })

    return this.handlePromise(p, urlParams)
  }

  /**
   * Submit an HTTP POST request.
   * @param jsonBody The request body.
   */
  post = (jsonBody = {}) => {
    if (this.debug) {
      console.log(`${this.url} httpHelder - request: `, jsonBody)
    }
    const csrfToken = Cookies.get('csrf_token')
    const promise = fetch(this.url, {
      method: 'POST',
      credentials: 'include',
      body: JSON.stringify(jsonBody),
      headers: { 'X-CSRFToken': csrfToken },
    })

    return this.handlePromise(promise, jsonBody)
  }

  /**
   * Shared code to process the Promise object returned by fetch(..)
   * @param promise
   * @param onSuccessArg
   */
  handlePromise = (promise, onSuccessArg) => {
    return promise.then((response) => {
      if (response.status === 401 && !window.location.href.includes('login')) {
        window.location.href = `${window.location.origin}/login?next=${window.location.href.replace(window.location.origin, '')}`
      }
      if (!response.ok) {
        console.log('ERROR: ', response.statusText, response.status, response)
        const throwJsonError = (responseJson) => {
          const message = responseJson.error || responseJson.message || `${response.statusText.toLowerCase()} (${response.status})`
          const err = new Error(message)
          err.body = responseJson
          throw err
        }
        return response.json().then(throwJsonError, () => throwJsonError({}))
      }
      try {
        return response.json()
      } catch (exception) {
        throw response.body
      }
    })
      .then((responseJson) => {
        if (this.debug) {
          console.log(`${this.url} httpHelder - response: `, responseJson)
        }
        if (this.onSuccess) {
          this.onSuccess(responseJson, onSuccessArg)
        }

        if (this.onClear) {
          this.httpPostId++
          return delay(this.delayBeforeClearing, this.httpPostId)
        }
        return -1
      })
      .catch((exception) => {
        console.log(exception)
        if (this.onError) {
          this.onError(exception)
        }

        //this.httpPostId++
        return -1 // don't ever hide the error message
      })
      .then((httpPostId) => {
        if (this.onClear && httpPostId === this.httpPostId) {
          this.onClear(httpPostId)
        }
      })
  }
}

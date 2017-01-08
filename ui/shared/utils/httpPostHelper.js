import delay from 'timeout-as-promise'

/**
 * Encapsulates the cycle of:
 * 1. sending an HTTP POST request to the server
 * 2. calling an onSuccess or onError handler with the response.
 * 3. setting a timer, and then clearing any notification message after a few seconds, assuming
 *    no new POST request was started.
 */
export class HttpPost {

  /**
   * Creates a new HttpPost helper.
   * @param url {string} The URL to send the request to.
   * @param onSuccess {function} optional handler called if server responds with status code 200
   * @param onError {function} optional handler called if server responds with a code other than 200
   * @param onClear {function} optional handler called some time after the onSuccess or onError handler is called
   * @param delayBeforeClearing {number} milliseconds delay before calling the onClear handler
   */
  constructor(url, onSuccess = null, onError = null, onClear = null, delayBeforeClearing = 2000) {
    this.url = url
    this.httpPostId = 0
    this.onSuccess = onSuccess
    this.onError = onError
    this.onClear = onClear
    this.delayBeforeClearing = delayBeforeClearing
  }

  /**
   * Submit an HTTP POST request.
   * @param jsonObj The request body.
   */
  submit = (submittedJson) => {
    fetch(this.url, {
      method: 'POST',
      credentials: 'include',
      body: JSON.stringify(submittedJson),
    })
      .then((response) => {
        if (!response.ok) {
          console.log('ERROR: ', response.statusText, response.status, response)
          throw new Error(`${response.statusText.toLowerCase()} (${response.status})`)
        }
        return response.json()
      })
      .then((responseJson) => {
        if (this.onSuccess) {
          this.onSuccess(responseJson, submittedJson)
        }

        if (this.onClear) {
          this.httpPostId++
          return delay(this.delayBeforeClearing, this.httpPostId)
        }
        return -1
      })
      .catch((exception) => {
        if (this.onError) {
          this.onError(exception)
        }

        //this.httpPostId++
        return -1  // don't ever hide the error message
      })
      .then((httpPostId) => {
        if (this.onClear && httpPostId === this.httpPostId) {
          this.onClear(httpPostId)
        }
      })
  }
}

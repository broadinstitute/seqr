import delay from 'timeout-as-promise'

export class HttpPost {

  constructor(url, onSuccess = null, onError = null, onClear = null, delayBeforeClearing = 2000) {
    this.url = url
    this.saveStatusEventId = 0
    this.onSuccess = onSuccess
    this.onError = onError
    this.onClear = onClear
    this.delayBeforeClearing = delayBeforeClearing
  }

  submit = (jsonObj) => {
    fetch(this.url, {
      method: 'POST',
      credentials: 'include',
      body: JSON.stringify(jsonObj),
    })
      .then((response) => {
        if (!response.ok) {
          console.log('ERROR: ', response.statusText, response.status, response)
          throw new Error(`${response.statusText.toLowerCase()} (${response.status})`)
        }
        return response
      })
      .then((response) => {
        if (this.onSuccess) {
          this.onSuccess(response, jsonObj)
        }

        if (this.onClear) {
          this.saveStatusEventId++
          return delay(this.delayBeforeClearing, this.saveStatusEventId)
        }
        return -1
      })
      .catch((exception) => {
        if (this.onError) {
          this.onError(exception)
        }

        //this.saveStatusEventId++
        return -1  // don't ever hide the error message
      })
      .then((eventId) => {
        //console.log(eventId, this.saveStatusEventId)
        if (this.onClear && eventId === this.saveStatusEventId) {
          this.onClear(eventId)
        }
      })
  }
}

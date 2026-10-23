package org.aief.personalautomator

class RequestFailure(val safeMessage: String) : Exception(safeMessage)

/** Messages never include exception text, response bodies, URLs with credentials, or headers. */
fun requestFailureMessage(error: Throwable): String = when (error) {
    is RequestFailure -> error.safeMessage
    is java.net.SocketTimeoutException -> "Request timed out. Check OmniRoute and its upstream provider."
    is java.net.ConnectException -> "Cannot connect to OmniRoute. Check that it is running on this tablet at port 20128."
    is java.net.UnknownHostException -> "Server address could not be resolved. Check the connection URL."
    is javax.net.ssl.SSLException -> "HTTPS certificate or TLS connection failed."
    is org.json.JSONException -> "Server returned an invalid proposal format. Nothing executed."
    is IllegalArgumentException -> "Invalid connection settings or unsupported proposal. Check URL, token format and model."
    else -> "Connection or credential storage failed. Re-save the connection or forget it and enter it again."
}

fun httpFailure(status: Int): RequestFailure = RequestFailure(when (status) {
    401 -> "HTTP 401: token rejected. Use an OmniRoute inference API token."
    403 -> "HTTP 403: token does not have permission for this request."
    402 -> "HTTP 402: provider credit or billing requirement. Check OmniRoute."
    404 -> "HTTP 404: endpoint or model not found. Check OmniRoute's enabled routes."
    429 -> "HTTP 429: provider quota or rate limit reached. Check OmniRoute."
    in 300..399 -> "Server returned a redirect, which this app blocks to protect credentials."
    in 500..599 -> "HTTP $status: OmniRoute, bridge or upstream provider failed. Check its logs."
    else -> "HTTP $status: server rejected the request. Nothing executed."
})

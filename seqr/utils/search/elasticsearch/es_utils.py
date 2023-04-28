from elasticsearch.exceptions import ConnectionError as EsConnectionError, TransportError


class InvalidIndexException(Exception):
    pass


ES_EXCEPTION_ERROR_MAP = {
    InvalidIndexException: 400,
    EsConnectionError: 504,
    TransportError: lambda e: int(e.status_code) if e.status_code != 'N/A' else 400,
}
ES_EXCEPTION_MESSAGE_MAP = {
    EsConnectionError: str,
    TransportError: lambda e: '{}: {} - {} - {}'.format(e.__class__.__name__, e.status_code, repr(e.error), _get_transport_error_type(e.info)),
}
ES_ERROR_LOG_EXCEPTIONS = {InvalidIndexException}


def _get_transport_error_type(error):
    error_type = 'no detail'
    if isinstance(error, dict):
        root_cause = error.get('root_cause')
        error_info = error.get('error')
        if (not root_cause) and isinstance(error_info, dict):
            root_cause = error_info.get('root_cause')

        if root_cause:
            error_type = root_cause[0].get('type') or root_cause[0].get('reason')
        elif error_info and not isinstance(error_info, dict):
            error_type = repr(error_info)
    return error_type

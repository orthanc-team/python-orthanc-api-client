
class OrthancApiException(Exception):

    def __init__(self, msg = "Unknown Orthanc Rest API exception", url = None):
        self.msg = msg
        self.url = url

    def __str__(self):
        return f"Orthanc API exception: '{self.msg}' while accessing '{self.url}'"


class ConnectionError(OrthancApiException):
    def __init__(self, msg = "Could not connect to Orthanc.", url = None):
        super().__init__(msg = msg, url = url)


class TimeoutError(OrthancApiException):
    def __init__(self, msg = "Timeout.  Orthanc took too long to respond.", url = None):
        super().__init__(msg = msg, url = url)

class TooManyResourcesFound(OrthancApiException):
    def __init__(self, msg = "Too many resources found with the same id.", url = None):
        super().__init__(msg = msg, url = url)


class HttpError(OrthancApiException):

    def __init__(self, http_status_code = None, msg = "Unknown Orthanc HTTP Rest API exception", url = None, request_response = None):
        super().__init__(msg = msg, url = url)
        self.http_status_code = http_status_code
        self.request_response = request_response

    def __str__(self):
        orthanc_error = (self.request_response.text if self.request_response is not None else "")
        return f"Orthanc HTTP API exception: '{self.http_status_code} - {self.msg}' while accessing '{self.url}' - Orthanc error: '{orthanc_error}'"


class ResourceNotFound(HttpError):
    def __init__(self, msg = "Resource not found.  The resource you're trying to access does not exist in Orthanc.", url = None):
        super().__init__(http_status_code = 404, msg = msg, url = url)

class NotAuthorized(HttpError):
    def __init__(self, http_status_code, msg = "Not authorized.  Make sure to provide login/pwd.", url = None):
        super().__init__(http_status_code = http_status_code, msg = msg, url = url)


class BadFileFormat(HttpError):
    """ Bad file format while uploading a DICOM file"""
    def __init__(self, http_error, msg = "Bad file format"):
        super().__init__(http_status_code = http_error.http_status_code, msg = msg, url = http_error.url)

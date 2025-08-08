"""
This file contains all the exceptions that are to be used across the product
"""


class ValidationException(Exception):
    """
    This exception is raise when ever you have a validation exception that you want to raise as a 400 in your api response
    """

    def __init__(self, error_code=None, description=None, message=None):
        self.error_code = error_code or "0002"
        self.message = message or "Validation Exception"
        self.decription = description

    def __str__(self):
        return "Error Message: %s" % (self.message)


class RateLimitException(Exception):
    """
    This exception is to be raised when you are querying a service and you are rate limited.
    """

    def __init__(self, error_code=None, description=None, message=None):
        self.error_code = error_code or "0002"
        self.message = message or "Validation Exception"
        self.decription = description

    def __str__(self):
        return "Error Message: %s" % (self.message)


class DBValidationException(Exception):
    """
    This Exception is to be raised when you have a validation error while writing to the database.
    """

    def __init__(self, error_code=None, description=None, message=None):
        self.error_code = error_code or "0002"
        self.message = message or "Validation Exception"
        self.decription = description

    def __str__(self):
        return "Error Message: %s" % (self.message)


class DBException(Exception):
    """
    This exception is to be raised when database exceptions are encountered.
    """

    def __init__(self, description=None, message=None):
        self.error_code = 500
        self.message = message or "DB Exception"
        self.decription = description

    def __str__(self):
        return "Error Message: %s" % (self.message)


class PermissionDeniedException(Exception):
    """
    This exception is raised when you have permissions issues in your code or apis.
    """

    def __init__(self, error_code=None, description=None, message=None):
        self.error_code = error_code or "422"
        self.message = message or "Permission Denied Exception"
        self.decription = description

    def __str__(self):
        return "Error Message: %s" % (self.message)


class InvalidStateException(Exception):
    """
    use this exception when ever you are stuck in a scenario when you encounter a code state where in your
    code logic is not aware of what to be done. we generally raise this as a 500 and treat this as a P0.
    """

    def __init__(self, description=None, message=None):
        self.error_code = 500
        self.message = message or "Invalid State Exception"
        self.decription = description

    def __str__(self):
        return "Error Message: %s" % (self.message)


class ResourceNotFoundException(Exception):
    """
    Related to databases or an api, raised when an object is not found in database.
    """

    def __init__(self, error_code=None, description=None, message=None):
        self.error_code = error_code or "0002"
        self.message = message or "Validation Exception"
        self.decription = description

    def __str__(self):
        return "Error Message: %s" % (self.message)


class InsufficientFundsException(Exception):
    """
    Related to databases or an api, when a user does not have sufficient funds.
    """

    def __init__(self, error_code=None, description=None, message=None):
        self.error_code = error_code or "402"
        self.message = message or "Insufficient Funds Exception"
        self.decription = description

    def __str__(self):
        return "Error Message: %s" % (self.message)


class PaymentAlreadyExistsException(Exception):
    """
    Related to databases or an api, raised when a payment record is alredy existing.
    helpful to send 201 response code.
    """

    def __init__(self, error_code=None, message=None, payment=None):
        self.error_code = error_code or "201"
        self.message = message or "Payment already exists Exception"
        self.payment = payment

    def __str__(self):
        return "Error Message: %s" % (self.message)


class UnsupportedMediaTypeException(Exception):
    """
    Raise an exception when you have an unsupported media type exception.
    Will be used while dropping a file or uploading a file to some service.
    """

    def __init__(self, error_code=None, description=None, message=None):
        self.error_code = error_code or "415"
        self.message = message or "Unsupported Media Type Exception"
        self.decription = description

    def __str__(self):
        return "Error Message: %s" % (self.message)


class ModelException(Exception):
    """
    This exception is to be raised when we have an ai model exception
    """

    def __init__(self, error_code=None, description=None, message=None):
        self.error_code = error_code or "529"
        self.message = message or "Model Exception"
        self.decription = description

    def __str__(self):
        return "Error Message: %s" % (self.message)


class LockTimeoutException(Exception):
    """
    This exception occurs when database lock acquisition is timedout.
    """

    def __init__(self, error_code=None, description=None, message=None):
        self.error_code = error_code or "423"
        self.message = message or "Lock Timeout Exception"
        self.decription = description

    def __str__(self):
        return "Error Message: %s" % (self.message)


class LockContentionException(Exception):
    """
    This exception is to be raised when database is trying to query a locked row.
    """

    def __init__(self, error_code=None, description=None, message=None):
        self.error_code = error_code or "423"
        self.message = message or "Lock Contention Exception"
        self.decription = description

    def __str__(self):
        return "Error Message: %s" % (self.message)

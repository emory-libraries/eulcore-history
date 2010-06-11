from eulcore.existdb.db import ExistDBException

class DoesNotExist(ExistDBException):
    "The query returned no results when exactly one was expected."
    silent_variable_failure = True

class ReturnedMultiple(ExistDBException):
    "The query returned multiple results when only one was expected."
    pass

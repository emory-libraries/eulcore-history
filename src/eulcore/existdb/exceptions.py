class DoesNotExist(Exception):
    "The query returned no results when exactly one was expected."
    silent_variable_failure = True

class ReturnedMultiple(Exception):
    "The query returned multiple results when only one was expected."
    pass

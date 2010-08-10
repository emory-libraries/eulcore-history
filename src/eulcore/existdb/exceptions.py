# file existdb\exceptions.py
# 
#   Copyright 2010 Emory University General Library
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from eulcore.existdb.db import ExistDBException

class DoesNotExist(ExistDBException):
    "The query returned no results when exactly one was expected."
    silent_variable_failure = True

class ReturnedMultiple(ExistDBException):
    "The query returned multiple results when only one was expected."
    pass

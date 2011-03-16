# file binfile.py
#
#   Copyright 2011 Emory University General Library
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

'''Map binary data on-disk to read-only Python objects.

This module facilitates exposing stored binary data using common Pythonic
idioms. Fields in relocatable binary objects map to Python attributes using
a priori knowledge about how the binary structure is organized. This is akin
to the standard :mod:`struct` module, but with more flexibility in placement
and size, at the cost of more verbose structure definitions and support only
for file-based structures.

This package exports the following names:
 * :class:`BinaryStructure` -- a base class for binary data structures
 * :class:`ByteField` -- a field that maps fixed-length binary data to
   Python strings
 * :class:`LengthPrependedStringField` -- a field that maps variable-length
   binary strings to Python strings
 * :class:`IntegerField` -- a field that maps fixed-length binary data to
   Python numbers
'''

from mmap import mmap

__all__ = [ 'BinaryStructure', 'ByteField', 'LengthPrependedStringField',
            'IntegerField' ]

class BinaryStructure(object):
    """A superclass for binary data structures superimposed over files.

    Typical users will create a subclass containing field objects (e.g.,
    :class:`ByteField`, :class:`IntegerField`). Each subclass instance is
    created with a file and with an optional offset into that file. When
    code accesses fields on the instance, they are calculated from the
    underlying binary file data.

    Instead of a file, it is occasionally appropriate to overlay an
    :class:`~mmap.mmap` structure (from the :mod:`mmap` standard library).
    This happens most often when one ``BinaryStructure`` instance creates
    another, passing ``self.mmap`` to the secondary object's constructor. In
    this case, the caller may specify the `mm` argument instead of an
    `fobj`.

    :param fobj: a file object or filename to overlay
    :param mm: a :class:`~mmap.mmap` object to overlay
    :param offset: the offset into the file where the structured data begins
    """

    def __init__(self, fobj=None, mm=None, offset=0):
        if mm is not None:
            self.mmap = mm
        else:
            if isinstance(fobj, str):
                fobj = open(fobj)
            self.mmap = mmap(fobj.fileno(), 0, prot=1) # read-only for now
        self._offset = offset


class ByteField(object):
    """A field mapping fixed-length binary data to Python strings.

    :param start: The offset into the structure of the beginning of the
      byte data.
    :param end: The offset into the structure of the end of the byte data.
      This is actually one past the last byte of data, so a four-byte
      ``ByteField`` starting at index 4 would be defined as
      ``ByteField(4, 8)`` and would include bytes 4, 5, 6, and 7 of the
      binary structure.

    Typical users will create a `ByteField` inside a :class:`BinaryStructure`
    subclass definition::

        class MyObject(BinaryStructure):
            myfield = ByteField(0, 4) # the first 4 bytes of the file

    When you instantiate the subclass and access the field, its value will
    be the literal bytes at that location in the structure::

        >>> o = MyObject('file.bin')
        >>> o.myfield
        'ABCD'
    """

    def __init__(self, start, end):
        self.start = start
        self.end = end

    def __get__(self, obj, owner):
        return obj.mmap[self.start + obj._offset : self.end + obj._offset]


class LengthPrependedStringField(object):
    """A field mapping variable-length binary strings to Python strings.

    This field accesses strings encoded with their length in their first
    byte and string data following that byte.

    :param offset: The offset of the single-byte string length.

    Typical users will create a ``LengthPrependedStringField`` inside a
    :class:`BinaryStructure` subclass definition::

        class MyObject(BinaryStructure):
            myfield = LengthPrependedStringField(0)

    When you instantiate the subclass and access the field, its length will
    be read from that location in the structure, and its data will be the
    bytes immediately following it. So with a file whose first bytes are
    ``'\x04ABCD'``::

        >>> o = MyObject('file.bin')
        >>> o.myfield
        'ABCD'
    """

    def __init__(self, offset):
        self.offset = offset

    def __get__(self, obj, owner):
        length_offset = self.offset + obj._offset
        length = ord(obj.mmap[length_offset])
        data_offset = length_offset + 1
        return obj.mmap[data_offset:data_offset + length]


class IntegerField(ByteField):
    """A field mapping fixed-length binary data to Python numbers.

    This field accessses arbitrary-length integers encoded as binary data.
    Currently only `big-endian <http://en.wikipedia.org/wiki/Endianness>`_,
    unsigned integers are supported.

    :param start: The offset into the structure of the beginning of the
      byte data.
    :param end: The offset into the structure of the end of the byte data.
      This is actually one past the last byte of data, so a four-byte
      ``IntegerField`` starting at index 4 would be defined as
      ``IntegerField(4, 8)`` and would include bytes 4, 5, 6, and 7 of the
      binary structure.

    Typical users will create an `IntegerField` inside a
    :class:`BinaryStructure` subclass definition::

        class MyObject(BinaryStructure):
            myfield = IntegerField(3, 6) # integer encoded in bytes 3, 4, 5

    When you instantiate the subclass and access the field, its value will
    be big-endian unsigned integer encoded at that location in the
    structure. So with a file whose bytes 3, 4, and 5 are '\x00\x01\x04'::

        >>> o = MyObject('file.bin')
        >>> o.myfield
        260
    """
    def __get__(self, obj, owner):
        bytes = ByteField.__get__(self, obj, owner)
        val = 0
        for byte in bytes:
            val *= 256
            val += ord(byte)
        return val

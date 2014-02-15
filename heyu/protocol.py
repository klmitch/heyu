# Copyright 2014 Rackspace
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import msgpack


# The current protocol version.  An entry for this must exist in the
# _versions dictionary.
_curr_version = 0

# Describes the known message types in a given protocol version.  For
# each version, the value is a dictionary mapping recognized message
# types to a dictionary having the keys "required" and "defaults".
# The value of "required" is a set containing the arguments that the
# message must contain, and the value of "defaults" is a dictionary
# mapping optional arguments to the default value that should be
# assumed for them.
_versions = {
    0: {
    },
}


class Message(object):
    """
    Represent a protocol message.  The ``msg_type`` property
    identifies the type of the message, and ``version`` identifies the
    protocol version.  Other attributes are arguments for the message.
    The interesting methods are ``from_frame()`` and ``to_frame()``.
    Note that, once constructed, a ``Message`` is immutable.
    """

    @classmethod
    def from_frame(cls, frame):
        """
        Construct a ``Message`` from a raw binary frame.

        :param frame: The binary frame.

        :returns: A constructed ``Message`` instance.
        """

        # Load the data
        data = msgpack.loads(frame)

        # A PDU must be a msgpack-encoded dict
        if not isinstance(data, dict):
            raise ValueError('invalid PDU')

        # It must always have a __version__ and a type
        try:
            version = data['__version__']
            msg_type = data['msg_type']
        except KeyError as e:
            raise ValueError("missing required PDU field %s" % str(e))

        # Construct a message
        return cls(msg_type, __version__=version, **dict(
            (k, v) for k, v in data.items()
            if k not in ('__version__', 'msg_type')))

    def __init__(self, msg_type, **args):
        """
        Construct a ``Message`` instance.  Keyword parameters other than
        the required ``msg_type`` parameter are taken to be arguments
        for the message.

        :param msg_type: The type of the message.  A string.
        """

        # Extract the desired protocol specification
        _version = args.pop('__version__', _curr_version)

        # Make sure we know that version
        if _version not in _versions:
            raise ValueError("cannot handle PDUs of version %d" % _version)

        # Save the basic data about the message
        self._version = _version
        self._msg_type = msg_type

        # Make sure we have all required arguments for the message
        # type and cache the defaults
        self._defaults = {}
        if msg_type in _versions[_version]:
            # Cache the defaults
            self._defaults = _versions[_version][msg_type].get('defaults', {})

            for key in _versions[_version][msg_type].get('required', set()):
                if key not in args:
                    raise ValueError("missing required PDU field '%s' for "
                                     "'%s' messages" % (key, msg_type))

        # Save the arguments
        self._args = dict((k, v) for k, v in args.items()
                          if k not in self._defaults or v != self._defaults[k])

    def __getattr__(self, name):
        """
        Retrieve an argument from the message.

        :param name: The name of the message argument.

        :returns: The value of that argument, or a default, if one was
                  provided.  Note that an ``AttributeError`` is raised
                  if the argument wasn't passed to the constructor and
                  no default was provided.
        """

        if name not in self._args and name not in self._defaults:
            raise AttributeError("'%s' object has no attribute '%s'" %
                                 (self.__class__.__name__, name))

        return self._args.get(name, self._defaults.get(name))

    @property
    def version(self):
        """
        Retrieve the version of the protocol message.
        """

        return self._version

    @property
    def msg_type(self):
        """
        Retrieve the type of the message.
        """

        return self._msg_type

    @property
    def known(self):
        """
        A boolean value indicating whether the message type is recognized.
        A ``True`` value indicates that the message type is known.
        """

        return self._msg_type in _versions[self._version]

    def to_frame(self):
        """
        Construct a binary frame from the message.

        :returns: The binary frame.
        """

        # Build the frame data
        data = self._args.copy()
        data['msg_type'] = self._msg_type
        data['__version__'] = self._version

        # Return the actual binary data
        return msgpack.dumps(data)

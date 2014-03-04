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


# The urgency levels
URGENCY_LOW = 0
URGENCY_NORMAL = 1
URGENCY_CRITICAL = 2

# A name to level map
urgency_map = {
    'low': URGENCY_LOW,
    'normal': URGENCY_NORMAL,
    'critical': URGENCY_CRITICAL,
}

# A level to name map
urgency_names = dict((v, k) for k, v in urgency_map.items())

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
        'notify': {
            'required': set(['app_name', 'summary', 'body']),
            'defaults': {
                'urgency': URGENCY_LOW,
                'category': None,
                'id': None,
            },
        },
        'accepted': {
            'required': set(['id']),
        },
        'subscribe': {},
        'subscribed': {},
        'goodbye': {},
        'error': {
            'required': set(['reason']),
        },
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

        # Construct a message; we pass the frame in to prime the frame
        # cache
        return cls(msg_type, __version__=version, __frame__=frame, **dict(
            (k, v) for k, v in data.items()
            if k not in ('__version__', 'msg_type')))

    def __init__(self, msg_type, **args):
        """
        Construct a ``Message`` instance.  Keyword parameters other than
        the required ``msg_type`` parameter are taken to be arguments
        for the message.

        :param msg_type: The type of the message.  A string.
        """

        # Extract the message protocol version and bare frame
        version = args.pop('__version__', _curr_version)
        frame = args.pop('__frame__', None)

        # Make sure we know that version
        if version not in _versions:
            raise ValueError("cannot handle PDUs of version %d" % version)

        # Save the basic data about the message
        self._version = version
        self._msg_type = msg_type

        # Make sure we have all required arguments for the message
        # type and cache the defaults
        self._defaults = {}
        if msg_type in _versions[version]:
            # Cache the defaults
            self._defaults = _versions[version][msg_type].get('defaults', {})

            for key in _versions[version][msg_type].get('required', set()):
                if key not in args:
                    raise ValueError("missing required PDU field '%s' for "
                                     "'%s' messages" % (key, msg_type))

        # Save the arguments
        self._args = dict((k, v) for k, v in args.items()
                          if k not in self._defaults or v != self._defaults[k])

        # Set up the frame cache
        self._frame_cache = {}
        if frame is not None:
            self._frame_cache[version] = frame

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

    def to_frame(self, version=_curr_version):
        """
        Construct a binary frame from the message.

        :param version: The protocol version to send.

        :returns: The binary frame.
        """

        if version not in self._frame_cache:
            # Can only handle _curr_version
            if version != _curr_version:
                raise ValueError('cannot serialize into version %s' % version)

            # Build the frame data
            data = self._args.copy()
            data['msg_type'] = self._msg_type
            data['__version__'] = self._version

            # Return the actual binary data
            self._frame_cache[version] = msgpack.dumps(data)

        return self._frame_cache[version]

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

import unittest

import mock

from heyu import protocol


class MessageTest(unittest.TestCase):
    @mock.patch('msgpack.loads', return_value=[])
    @mock.patch.object(protocol.Message, '__init__', return_value=None)
    def test_from_frame_bad_pdu(self, mock_init, mock_loads):
        self.assertRaises(ValueError, protocol.Message.from_frame, 'frame')
        mock_loads.assert_called_once_with('frame')
        self.assertFalse(mock_init.called)

    @mock.patch('msgpack.loads', return_value={
        '__version__': 5,
    })
    @mock.patch.object(protocol.Message, '__init__', return_value=None)
    def test_from_frame_no_type(self, mock_init, mock_loads):
        self.assertRaises(ValueError, protocol.Message.from_frame, 'frame')
        mock_loads.assert_called_once_with('frame')
        self.assertFalse(mock_init.called)

    @mock.patch('msgpack.loads', return_value={
        'msg_type': 'test',
    })
    @mock.patch.object(protocol.Message, '__init__', return_value=None)
    def test_from_frame_no_version(self, mock_init, mock_loads):
        self.assertRaises(ValueError, protocol.Message.from_frame, 'frame')
        mock_loads.assert_called_once_with('frame')
        self.assertFalse(mock_init.called)

    @mock.patch('msgpack.loads', return_value={
        '__version__': 5,
        'msg_type': 'test',
        'a': 1,
        'b': 2,
        'c': 3,
    })
    @mock.patch.object(protocol.Message, '__init__', return_value=None)
    def test_from_frame_happy_path(self, mock_init, mock_loads):
        msg = protocol.Message.from_frame('frame')

        self.assertTrue(isinstance(msg, protocol.Message))
        mock_loads.assert_called_once_with('frame')
        mock_init.assert_called_once_with(
            'test', __version__=5, __frame__='frame', a=1, b=2, c=3)

    @mock.patch.dict(protocol._versions, {
        0: {'test': {}},
    })
    def test_init_wrong_version(self):
        self.assertRaises(ValueError, protocol.Message, 'test', __version__=2)

    @mock.patch.dict(protocol._versions, {
        0: {'test': {'required': set(['spam'])}},
    })
    def test_init_missing_argument(self):
        self.assertRaises(ValueError, protocol.Message, 'test')

    @mock.patch.dict(protocol._versions, {
        0: {'test': {}},
    })
    def test_init_basic(self):
        msg = protocol.Message('test', a=1, b=2, c=3)

        self.assertEqual(msg._version, protocol._curr_version)
        self.assertEqual(msg._msg_type, 'test')
        self.assertEqual(msg._defaults, {})
        self.assertEqual(msg._args, {'a': 1, 'b': 2, 'c': 3})
        self.assertEqual(msg._frame_cache, {})

    @mock.patch.dict(protocol._versions, {
        0: {'test': {}},
    })
    def test_init_primed(self):
        msg = protocol.Message('test', a=1, b=2, c=3, __frame__='frame')

        self.assertEqual(msg._version, protocol._curr_version)
        self.assertEqual(msg._msg_type, 'test')
        self.assertEqual(msg._defaults, {})
        self.assertEqual(msg._args, {'a': 1, 'b': 2, 'c': 3})
        self.assertEqual(msg._frame_cache, {protocol._curr_version: 'frame'})

    @mock.patch.dict(protocol._versions, {
        0: {'test': {'defaults': {'def': 'ault'}}},
    })
    def test_init_defaults(self):
        msg = protocol.Message('test', a=1, b=2, c=3)

        self.assertEqual(msg._version, protocol._curr_version)
        self.assertEqual(msg._msg_type, 'test')
        self.assertEqual(msg._defaults, {'def': 'ault'})
        self.assertEqual(msg._args, {'a': 1, 'b': 2, 'c': 3})
        self.assertEqual(msg._frame_cache, {})

    @mock.patch.dict(protocol._versions, {
        0: {'test': {'defaults': {'b': 2, 'c': 4, 'd': 5}}},
    })
    def test_init_defaults_collapse(self):
        msg = protocol.Message('test', a=1, b=2, c=3)

        self.assertEqual(msg._version, protocol._curr_version)
        self.assertEqual(msg._msg_type, 'test')
        self.assertEqual(msg._defaults, {'b': 2, 'c': 4, 'd': 5})
        self.assertEqual(msg._args, {'a': 1, 'c': 3})
        self.assertEqual(msg._frame_cache, {})

    @mock.patch.dict(protocol._versions, {
        0: {'test': {}},
        1: {'test1': {}},
    })
    def test_init_alt_version(self):
        msg = protocol.Message('test1', a=1, b=2, c=3, __version__=1)

        self.assertEqual(msg._version, 1)
        self.assertEqual(msg._msg_type, 'test1')
        self.assertEqual(msg._defaults, {})
        self.assertEqual(msg._args, {'a': 1, 'b': 2, 'c': 3})
        self.assertEqual(msg._frame_cache, {})

    @mock.patch.dict(protocol._versions, {
        0: {'test': {}},
    })
    def test_init_unknown_type(self):
        msg = protocol.Message('other', a=1, b=2, c=3)

        self.assertEqual(msg._version, protocol._curr_version)
        self.assertEqual(msg._msg_type, 'other')
        self.assertEqual(msg._defaults, {})
        self.assertEqual(msg._args, {'a': 1, 'b': 2, 'c': 3})
        self.assertEqual(msg._frame_cache, {})

    @mock.patch.dict(protocol._versions, {
        0: {'test': {'required': set(['spam'])}},
    })
    def test_init_required(self):
        msg = protocol.Message('test', a=1, b=2, c=3, spam='spam')

        self.assertEqual(msg._version, protocol._curr_version)
        self.assertEqual(msg._msg_type, 'test')
        self.assertEqual(msg._defaults, {})
        self.assertEqual(msg._args, {'a': 1, 'b': 2, 'c': 3,
                                     'spam': 'spam'})
        self.assertEqual(msg._frame_cache, {})

    @mock.patch.dict(protocol._versions, {
        0: {'test': {}},
    })
    def test_getattr_undefined(self):
        msg = protocol.Message('test')

        self.assertRaises(AttributeError, lambda: msg.spam)

    @mock.patch.dict(protocol._versions, {
        0: {'test': {}},
    })
    def test_getattr_argument_nodefault(self):
        msg = protocol.Message('test', spam='spam')

        self.assertEqual(msg.spam, 'spam')

    @mock.patch.dict(protocol._versions, {
        0: {'test': {'defaults': {'spam': 'default'}}},
    })
    def test_getattr_argument_withdefault(self):
        msg = protocol.Message('test', spam='spam')

        self.assertEqual(msg.spam, 'spam')

    @mock.patch.dict(protocol._versions, {
        0: {'test': {'defaults': {'spam': 'default'}}},
    })
    def test_getattr_default(self):
        msg = protocol.Message('test')

        self.assertEqual(msg.spam, 'default')

    @mock.patch.dict(protocol._versions, {
        0: {'test': {}},
    })
    def test_version(self):
        msg = protocol.Message('test')

        self.assertEqual(msg.version, protocol._curr_version)

    @mock.patch.dict(protocol._versions, {
        0: {'test': {}},
    })
    def test_msg_type(self):
        msg = protocol.Message('test')

        self.assertEqual(msg.msg_type, 'test')

    @mock.patch.dict(protocol._versions, {
        0: {'test': {}},
    })
    def test_known_known(self):
        msg = protocol.Message('test')

        self.assertEqual(msg.known, True)

    @mock.patch.dict(protocol._versions, {
        0: {'test': {}},
    })
    def test_known_unknown(self):
        msg = protocol.Message('other')

        self.assertEqual(msg.known, False)

    @mock.patch.dict(protocol._versions, {
        0: {'test': {}},
    })
    @mock.patch('msgpack.dumps', return_value='frame')
    def test_to_frame_uncached(self, mock_dumps):
        msg = protocol.Message('test', a=1, b=2, c=3)

        result = msg.to_frame()

        self.assertEqual(result, 'frame')
        mock_dumps.assert_called_once_with({
            'msg_type': 'test',
            '__version__': 0,
            'a': 1,
            'b': 2,
            'c': 3,
        })

    @mock.patch.dict(protocol._versions, {
        0: {'test': {}},
    })
    @mock.patch('msgpack.dumps', return_value='frame')
    def test_to_frame_cached(self, mock_dumps):
        msg = protocol.Message('test', a=1, b=2, c=3, __frame__='cached')

        result = msg.to_frame()

        self.assertEqual(result, 'cached')
        self.assertFalse(mock_dumps.called)

    @mock.patch.dict(protocol._versions, {
        0: {'test': {}},
    })
    @mock.patch('msgpack.dumps', return_value='frame')
    def test_to_frame_bad_version(self, mock_dumps):
        msg = protocol.Message('test', a=1, b=2, c=3)

        self.assertRaises(ValueError, msg.to_frame, -1)
        self.assertFalse(mock_dumps.called)

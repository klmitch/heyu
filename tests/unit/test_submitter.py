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

from __future__ import print_function

import io
import sys
import unittest

import mock

from heyu import protocol
from heyu import submitter
from heyu import util


class SubmitterApplicationTest(unittest.TestCase):
    @mock.patch('tendril.COBSFramer', return_value='framer')
    @mock.patch.object(protocol, 'Message', return_value=mock.Mock(**{
        'to_frame.return_value': 'message',
    }))
    @mock.patch.object(submitter.SubmitterApplication, 'send_frame')
    def test_init_basic(self, mock_send_frame, mock_Message, mock_COBSFramer):
        parent = mock.Mock()

        app = submitter.SubmitterApplication(parent, 'app', 'summary', 'body')

        self.assertEqual(parent, app.parent)
        mock_COBSFramer.assert_called_once_with(True)
        self.assertEqual('framer', parent.framers)
        mock_Message.assert_called_once_with(
            'notify', app_name='app', summary='summary', body='body')
        mock_send_frame.assert_called_once_with('message')

    @mock.patch('tendril.COBSFramer', return_value='framer')
    @mock.patch.object(protocol, 'Message', return_value=mock.Mock(**{
        'to_frame.return_value': 'message',
    }))
    @mock.patch.object(submitter.SubmitterApplication, 'send_frame')
    def test_init_extra(self, mock_send_frame, mock_Message, mock_COBSFramer):
        parent = mock.Mock()

        app = submitter.SubmitterApplication(parent, 'app', 'summary', 'body',
                                             'urgency', 'category', 'id')

        self.assertEqual(parent, app.parent)
        mock_COBSFramer.assert_called_once_with(True)
        self.assertEqual('framer', parent.framers)
        mock_Message.assert_called_once_with(
            'notify', app_name='app', summary='summary', body='body',
            urgency='urgency', category='category', id='id')
        mock_send_frame.assert_called_once_with('message')

    @mock.patch.object(submitter.SubmitterApplication, '__init__',
                       return_value=None)
    @mock.patch.object(submitter.SubmitterApplication, 'close')
    @mock.patch.object(protocol.Message, 'from_frame', return_value=mock.Mock(
        msg_type='accepted', id='notification-id'))
    @mock.patch('__builtin__.print')
    def test_recv_frame_accepted(self, mock_print, mock_from_frame,
                                 mock_close, mock_init):
        app = submitter.SubmitterApplication()

        app.recv_frame('frame')

        mock_from_frame.assert_called_once_with('frame')
        mock_print.assert_called_once_with('notification-id')
        mock_close.assert_called_once_with()

    @mock.patch.object(submitter.SubmitterApplication, '__init__',
                       return_value=None)
    @mock.patch.object(submitter.SubmitterApplication, 'close')
    @mock.patch.object(protocol.Message, 'from_frame', return_value=mock.Mock(
        msg_type='error', reason='something bad happened'))
    @mock.patch('__builtin__.print')
    def test_recv_frame_error(self, mock_print, mock_from_frame,
                              mock_close, mock_init):
        app = submitter.SubmitterApplication()

        app.recv_frame('frame')

        mock_from_frame.assert_called_once_with('frame')
        mock_print.assert_called_once_with(
            'Failed to submit notification: something bad happened',
            file=sys.stderr)
        mock_close.assert_called_once_with()

    @mock.patch.object(submitter.SubmitterApplication, '__init__',
                       return_value=None)
    @mock.patch.object(submitter.SubmitterApplication, 'close')
    @mock.patch.object(protocol.Message, 'from_frame', return_value=mock.Mock(
        msg_type='other'))
    @mock.patch('__builtin__.print')
    def test_recv_frame_unknown(self, mock_print, mock_from_frame,
                                mock_close, mock_init):
        app = submitter.SubmitterApplication()

        app.recv_frame('frame')

        mock_from_frame.assert_called_once_with('frame')
        mock_print.assert_called_once_with(
            'Unrecognized protocol message "other"',
            file=sys.stderr)
        mock_close.assert_called_once_with()

    @mock.patch.object(submitter.SubmitterApplication, '__init__',
                       return_value=None)
    @mock.patch.object(submitter.SubmitterApplication, 'close')
    @mock.patch.object(protocol.Message, 'from_frame',
                       side_effect=ValueError('bad frame'))
    @mock.patch('__builtin__.print')
    def test_recv_frame_parse_error(self, mock_print, mock_from_frame,
                                    mock_close, mock_init):
        app = submitter.SubmitterApplication()

        app.recv_frame('frame')

        mock_from_frame.assert_called_once_with('frame')
        mock_print.assert_called_once_with(
            'Failed to parse frame: bad frame',
            file=sys.stderr)
        mock_close.assert_called_once_with()


class SendNotificationTest(unittest.TestCase):
    @mock.patch.object(util, 'outgoing_endpoint', return_value='outgoing')
    @mock.patch.object(util, 'cert_wrapper', return_value='wrapper')
    @mock.patch('tendril.get_manager')
    @mock.patch('tendril.TendrilPartial', return_value='the_app')
    def test_basic(self, mock_TendrilPartial, mock_get_manager,
                   mock_cert_wrapper, mock_outgoing_endpoint):
        submitter.send_notification('hub', 'app', 'summary', 'body')

        mock_outgoing_endpoint.assert_called_once_with('hub')
        mock_get_manager.assert_called_once_with('tcp', 'outgoing')
        mock_get_manager.return_value.assert_has_calls([
            mock.call.start(),
            mock.call.connect('hub', 'the_app', 'wrapper'),
        ])
        mock_TendrilPartial.assert_called_once_with(
            submitter.SubmitterApplication,
            'app', 'summary', 'body', None, None, None)
        mock_cert_wrapper.assert_called_once_with(
            None, 'submitter', secure=True)

    @mock.patch.object(util, 'outgoing_endpoint', return_value='outgoing')
    @mock.patch.object(util, 'cert_wrapper', return_value='wrapper')
    @mock.patch('tendril.get_manager')
    @mock.patch('tendril.TendrilPartial', return_value='the_app')
    def test_extra(self, mock_TendrilPartial, mock_get_manager,
                   mock_cert_wrapper, mock_outgoing_endpoint):
        submitter.send_notification('hub', 'app', 'summary', 'body',
                                    'urgency', 'category', 'id',
                                    'cert_conf', False)

        mock_outgoing_endpoint.assert_called_once_with('hub')
        mock_get_manager.assert_called_once_with('tcp', 'outgoing')
        mock_get_manager.return_value.assert_has_calls([
            mock.call.start(),
            mock.call.connect('hub', 'the_app', 'wrapper'),
        ])
        mock_TendrilPartial.assert_called_once_with(
            submitter.SubmitterApplication,
            'app', 'summary', 'body', 'urgency', 'category', 'id')
        mock_cert_wrapper.assert_called_once_with(
            'cert_conf', 'submitter', secure=False)


class NormalizeArgsTest(unittest.TestCase):
    @mock.patch('os.path.expanduser', return_value='/home/dir/.heyu.hub')
    @mock.patch('__builtin__.open', side_effect=IOError())
    @mock.patch.object(util, 'parse_hub', return_value=('hub', 1234))
    @mock.patch('sys.argv', ['my/submitter'])
    def test_defaults(self, mock_parse_hub, mock_open, mock_expand_user):
        args = mock.Mock(hub=None, app_name=None, urgency=None)

        submitter._normalize_args(args)

        self.assertEqual(('127.0.0.1', util.HEYU_PORT), args.hub)
        self.assertEqual('submitter', args.app_name)
        self.assertEqual(None, args.urgency)
        mock_open.assert_called_once_with('/home/dir/.heyu.hub')
        self.assertFalse(mock_parse_hub.called)

    @mock.patch('os.path.expanduser', return_value='/home/dir/.heyu.hub')
    @mock.patch('__builtin__.open', return_value=io.BytesIO('hub\n'))
    @mock.patch.object(util, 'parse_hub', return_value=('hub', 1234))
    @mock.patch('sys.argv', ['my/submitter'])
    def test_read_hub(self, mock_parse_hub, mock_open, mock_expand_user):
        args = mock.Mock(hub=None, app_name=None, urgency=None)

        submitter._normalize_args(args)

        self.assertEqual(('hub', 1234), args.hub)
        self.assertEqual('submitter', args.app_name)
        self.assertEqual(None, args.urgency)
        mock_open.assert_called_once_with('/home/dir/.heyu.hub')
        mock_parse_hub.assert_called_once_with('hub')

    @mock.patch('os.path.expanduser', return_value='/home/dir/.heyu.hub')
    @mock.patch('__builtin__.open', side_effect=IOError())
    @mock.patch.object(util, 'parse_hub', return_value=('hub', 1234))
    @mock.patch('sys.argv', ['my/submitter'])
    def test_given_hub(self, mock_parse_hub, mock_open, mock_expand_user):
        args = mock.Mock(hub='hub', app_name=None, urgency=None)

        submitter._normalize_args(args)

        self.assertEqual(('hub', 1234), args.hub)
        self.assertEqual('submitter', args.app_name)
        self.assertEqual(None, args.urgency)
        self.assertFalse(mock_open.called)
        mock_parse_hub.assert_called_once_with('hub')

    @mock.patch('os.path.expanduser', return_value='/home/dir/.heyu.hub')
    @mock.patch('__builtin__.open', side_effect=IOError())
    @mock.patch.object(util, 'parse_hub', return_value=('hub', 1234))
    @mock.patch('sys.argv', ['my/submitter'])
    def test_given_app_name(self, mock_parse_hub, mock_open, mock_expand_user):
        args = mock.Mock(hub=None, app_name='myapp', urgency=None)

        submitter._normalize_args(args)

        self.assertEqual(('127.0.0.1', util.HEYU_PORT), args.hub)
        self.assertEqual('myapp', args.app_name)
        self.assertEqual(None, args.urgency)
        mock_open.assert_called_once_with('/home/dir/.heyu.hub')
        self.assertFalse(mock_parse_hub.called)

    @mock.patch('os.path.expanduser', return_value='/home/dir/.heyu.hub')
    @mock.patch('__builtin__.open', side_effect=IOError())
    @mock.patch.object(util, 'parse_hub', return_value=('hub', 1234))
    @mock.patch('sys.argv', ['my/submitter'])
    def test_given_urgency(self, mock_parse_hub, mock_open, mock_expand_user):
        args = mock.Mock(hub=None, app_name=None, urgency='LoW')

        submitter._normalize_args(args)

        self.assertEqual(('127.0.0.1', util.HEYU_PORT), args.hub)
        self.assertEqual('submitter', args.app_name)
        self.assertEqual(protocol.URGENCY_LOW, args.urgency)
        mock_open.assert_called_once_with('/home/dir/.heyu.hub')
        self.assertFalse(mock_parse_hub.called)

    @mock.patch('os.path.expanduser', return_value='/home/dir/.heyu.hub')
    @mock.patch('__builtin__.open', side_effect=IOError())
    @mock.patch.object(util, 'parse_hub', return_value=('hub', 1234))
    @mock.patch('sys.argv', ['my/submitter'])
    def test_bad_urgency(self, mock_parse_hub, mock_open, mock_expand_user):
        args = mock.Mock(hub=None, app_name=None, urgency='High')

        self.assertRaises(submitter.SubmitterException,
                          submitter._normalize_args, args)

        mock_open.assert_called_once_with('/home/dir/.heyu.hub')
        self.assertFalse(mock_parse_hub.called)

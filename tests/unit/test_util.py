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

import ConfigParser
import socket
import ssl
import unittest

import mock

from heyu import util


class TestException(Exception):
    pass


class ParseHubTest(unittest.TestCase):
    @mock.patch.object(socket, 'getaddrinfo',
                       side_effect=lambda a, b, c, d: [(1, 2, 3, '', (a, b))])
    def test_space(self, mock_getaddrinfo):
        self.assertRaises(util.HubException, util.parse_hub, 'bad hostname')
        self.assertFalse(mock_getaddrinfo.called)

    @mock.patch.object(socket, 'getaddrinfo',
                       side_effect=lambda a, b, c, d: [(1, 2, 3, '', (a, b))])
    def test_bracket(self, mock_getaddrinfo):
        self.assertRaises(util.HubException, util.parse_hub, 'bad[hostname')
        self.assertRaises(util.HubException, util.parse_hub, 'bad]hostname')
        self.assertRaises(util.HubException, util.parse_hub, '[]')
        self.assertFalse(mock_getaddrinfo.called)

    @mock.patch.object(socket, 'getaddrinfo',
                       side_effect=lambda a, b, c, d: [(1, 2, 3, '', (a, b))])
    def test_colon(self, mock_getaddrinfo):
        self.assertRaises(util.HubException, util.parse_hub, 'bad:hostname')
        self.assertRaises(util.HubException, util.parse_hub, 'bad:')
        self.assertFalse(mock_getaddrinfo.called)

    @mock.patch.object(socket, 'getaddrinfo',
                       side_effect=lambda a, b, c, d: [(1, 2, 3, '', (a, b))])
    def test_bad_ipv6(self, mock_getaddrinfo):
        self.assertRaises(util.HubException, util.parse_hub, '::1')
        self.assertRaises(util.HubException, util.parse_hub, '[::1')
        self.assertRaises(util.HubException, util.parse_hub, '::1]')
        self.assertFalse(mock_getaddrinfo.called)

    @mock.patch.object(socket, 'getaddrinfo',
                       side_effect=socket.gaierror(-2, 'Name or service '
                                                   'not known'))
    def test_unresolvable(self, mock_getaddrinfo):
        self.assertRaises(util.HubException, util.parse_hub, 'hostname')
        mock_getaddrinfo.assert_called_once_with(
            'hostname', util.HEYU_PORT, 0, socket.SOCK_STREAM)

    @mock.patch.object(socket, 'getaddrinfo',
                       side_effect=lambda a, b, c, d: [(1, 2, 3, '', (a, b))])
    def test_bare_hostname(self, mock_getaddrinfo):
        result = util.parse_hub('hostname')

        self.assertEqual(('hostname', util.HEYU_PORT), result)
        mock_getaddrinfo.assert_called_once_with(
            'hostname', util.HEYU_PORT, 0, socket.SOCK_STREAM)

    @mock.patch.object(socket, 'getaddrinfo',
                       side_effect=lambda a, b, c, d: [(1, 2, 3, '', (a, b))])
    def test_hostname_with_port(self, mock_getaddrinfo):
        result = util.parse_hub('hostname:1234')

        self.assertEqual(('hostname', 1234), result)
        mock_getaddrinfo.assert_called_once_with(
            'hostname', 1234, 0, socket.SOCK_STREAM)

    @mock.patch.object(socket, 'getaddrinfo',
                       side_effect=lambda a, b, c, d: [(1, 2, 3, '', (a, b))])
    def test_bare_ipv4(self, mock_getaddrinfo):
        result = util.parse_hub('127.0.0.1')

        self.assertEqual(('127.0.0.1', util.HEYU_PORT), result)
        mock_getaddrinfo.assert_called_once_with(
            '127.0.0.1', util.HEYU_PORT, 0, socket.SOCK_STREAM)

    @mock.patch.object(socket, 'getaddrinfo',
                       side_effect=lambda a, b, c, d: [(1, 2, 3, '', (a, b))])
    def test_ipv4_with_port(self, mock_getaddrinfo):
        result = util.parse_hub('127.0.0.1:1234')

        self.assertEqual(('127.0.0.1', 1234), result)
        mock_getaddrinfo.assert_called_once_with(
            '127.0.0.1', 1234, 0, socket.SOCK_STREAM)

    @mock.patch.object(socket, 'getaddrinfo',
                       side_effect=lambda a, b, c, d: [(1, 2, 3, '', (a, b))])
    def test_bare_ipv6(self, mock_getaddrinfo):
        result = util.parse_hub('[::1]')

        self.assertEqual(('::1', util.HEYU_PORT), result)
        mock_getaddrinfo.assert_called_once_with(
            '::1', util.HEYU_PORT, 0, socket.SOCK_STREAM)

    @mock.patch.object(socket, 'getaddrinfo',
                       side_effect=lambda a, b, c, d: [(1, 2, 3, '', (a, b))])
    def test_ipv6_with_port(self, mock_getaddrinfo):
        result = util.parse_hub('[::1]:1234')

        self.assertEqual(('::1', 1234), result)
        mock_getaddrinfo.assert_called_once_with(
            '::1', 1234, 0, socket.SOCK_STREAM)


class CertWrapperTest(unittest.TestCase):
    @mock.patch('os.path.expanduser', return_value='/home/dir/.heyu.cert')
    @mock.patch('ConfigParser.SafeConfigParser', return_value=mock.Mock(**{
        'read.return_value': [],
        'items.return_value': [],
    }))
    @mock.patch('tendril.TendrilPartial', return_value='wrapper')
    def test_insecure(self, mock_TendrilPartial, mock_SafeConfigParser,
                      mock_expanduser):
        result = util.cert_wrapper(None, 'test', secure=False)

        self.assertEqual(None, result)
        self.assertFalse(mock_expanduser.called)
        self.assertFalse(mock_SafeConfigParser.called)
        self.assertFalse(mock_TendrilPartial.called)

    @mock.patch('os.path.expanduser', return_value='/home/dir/.heyu.cert')
    @mock.patch('ConfigParser.SafeConfigParser', return_value=mock.Mock(**{
        'read.return_value': [],
        'items.return_value': [],
    }))
    @mock.patch('tendril.TendrilPartial', return_value='wrapper')
    def test_missing_conf(self, mock_TendrilPartial, mock_SafeConfigParser,
                          mock_expanduser):
        cp = mock_SafeConfigParser.return_value

        self.assertRaises(util.CertException, util.cert_wrapper, None, 'test')
        mock_expanduser.assert_called_once_with('~/.heyu.cert')
        mock_SafeConfigParser.assert_called_once_with()
        cp.read.assert_called_once_with('/home/dir/.heyu.cert')
        self.assertFalse(cp.items.called)
        self.assertFalse(mock_TendrilPartial.called)

    @mock.patch('os.path.expanduser', return_value='/home/dir/.heyu.cert')
    @mock.patch('ConfigParser.SafeConfigParser', return_value=mock.Mock(**{
        'read.return_value': [],
        'items.return_value': [],
    }))
    @mock.patch('tendril.TendrilPartial', return_value='wrapper')
    def test_bad_conf(self, mock_TendrilPartial, mock_SafeConfigParser,
                      mock_expanduser):
        cp = mock_SafeConfigParser.return_value

        self.assertRaises(util.CertException, util.cert_wrapper,
                          'bad[file', 'test')
        self.assertFalse(mock_expanduser.called)
        self.assertFalse(mock_SafeConfigParser.called)
        self.assertFalse(cp.items.called)
        self.assertFalse(mock_TendrilPartial.called)

    @mock.patch('os.path.expanduser', return_value='/home/dir/.heyu.cert')
    @mock.patch('ConfigParser.SafeConfigParser', return_value=mock.Mock(**{
        'read.return_value': ['/home/dir/.heyu.cert'],
        'items.side_effect': ConfigParser.NoSectionError('test'),
    }))
    @mock.patch('tendril.TendrilPartial', return_value='wrapper')
    def test_missing_profile(self, mock_TendrilPartial, mock_SafeConfigParser,
                             mock_expanduser):
        cp = mock_SafeConfigParser.return_value

        self.assertRaises(util.CertException, util.cert_wrapper, None, 'test')
        mock_expanduser.assert_called_once_with('~/.heyu.cert')
        mock_SafeConfigParser.assert_called_once_with()
        cp.read.assert_called_once_with('/home/dir/.heyu.cert')
        cp.items.assert_called_once_with('test')
        self.assertFalse(mock_TendrilPartial.called)

    @mock.patch('os.path.expanduser', return_value='/home/dir/.heyu.cert')
    @mock.patch('ConfigParser.SafeConfigParser', return_value=mock.Mock(**{
        'read.return_value': ['/home/dir/.heyu.cert'],
        'items.side_effect': TestException('test'),
    }))
    @mock.patch('tendril.TendrilPartial', return_value='wrapper')
    def test_unloadable_profile(self, mock_TendrilPartial,
                                mock_SafeConfigParser, mock_expanduser):
        cp = mock_SafeConfigParser.return_value

        self.assertRaises(util.CertException, util.cert_wrapper, None, 'test')
        mock_expanduser.assert_called_once_with('~/.heyu.cert')
        mock_SafeConfigParser.assert_called_once_with()
        cp.read.assert_called_once_with('/home/dir/.heyu.cert')
        cp.items.assert_called_once_with('test')
        self.assertFalse(mock_TendrilPartial.called)

    @mock.patch('os.path.expanduser', return_value='/home/dir/.heyu.cert')
    @mock.patch('ConfigParser.SafeConfigParser', return_value=mock.Mock(**{
        'read.return_value': ['/home/dir/.heyu.cert'],
        'items.return_value': [('cafile', 'ca'), ('certfile', 'cert')],
    }))
    @mock.patch('tendril.TendrilPartial', return_value='wrapper')
    def test_missing_keyfile(self, mock_TendrilPartial, mock_SafeConfigParser,
                             mock_expanduser):
        cp = mock_SafeConfigParser.return_value

        self.assertRaises(util.CertException, util.cert_wrapper, None, 'test')
        mock_expanduser.assert_called_once_with('~/.heyu.cert')
        mock_SafeConfigParser.assert_called_once_with()
        cp.read.assert_called_once_with('/home/dir/.heyu.cert')
        cp.items.assert_called_once_with('test')
        self.assertFalse(mock_TendrilPartial.called)

    @mock.patch('os.path.expanduser', return_value='/home/dir/.heyu.cert')
    @mock.patch('ConfigParser.SafeConfigParser', return_value=mock.Mock(**{
        'read.return_value': ['/home/dir/.heyu.cert'],
        'items.return_value': [('keyfile', 'key'), ('certfile', 'cert')],
    }))
    @mock.patch('tendril.TendrilPartial', return_value='wrapper')
    def test_missing_cafile(self, mock_TendrilPartial, mock_SafeConfigParser,
                            mock_expanduser):
        cp = mock_SafeConfigParser.return_value

        self.assertRaises(util.CertException, util.cert_wrapper, None, 'test')
        mock_expanduser.assert_called_once_with('~/.heyu.cert')
        mock_SafeConfigParser.assert_called_once_with()
        cp.read.assert_called_once_with('/home/dir/.heyu.cert')
        cp.items.assert_called_once_with('test')
        self.assertFalse(mock_TendrilPartial.called)

    @mock.patch('os.path.expanduser', return_value='/home/dir/.heyu.cert')
    @mock.patch('ConfigParser.SafeConfigParser', return_value=mock.Mock(**{
        'read.return_value': ['/home/dir/.heyu.cert'],
        'items.return_value': [('cafile', 'ca'), ('keyfile', 'key')],
    }))
    @mock.patch('tendril.TendrilPartial', return_value='wrapper')
    def test_missing_certfile(self, mock_TendrilPartial, mock_SafeConfigParser,
                              mock_expanduser):
        cp = mock_SafeConfigParser.return_value

        self.assertRaises(util.CertException, util.cert_wrapper, None, 'test')
        mock_expanduser.assert_called_once_with('~/.heyu.cert')
        mock_SafeConfigParser.assert_called_once_with()
        cp.read.assert_called_once_with('/home/dir/.heyu.cert')
        cp.items.assert_called_once_with('test')
        self.assertFalse(mock_TendrilPartial.called)

    @mock.patch('os.path.expanduser', return_value='/home/dir/.heyu.cert')
    @mock.patch('ConfigParser.SafeConfigParser', return_value=mock.Mock(**{
        'read.return_value': ['/home/dir/.heyu.cert'],
        'items.return_value': [
            ('cafile', 'ca'),
            ('keyfile', 'key'),
            ('certfile', 'cert'),
        ],
    }))
    @mock.patch('tendril.TendrilPartial', return_value='wrapper')
    def test_basic(self, mock_TendrilPartial, mock_SafeConfigParser,
                   mock_expanduser):
        cp = mock_SafeConfigParser.return_value

        result = util.cert_wrapper(None, 'test')

        self.assertEqual(result, 'wrapper')
        mock_expanduser.assert_called_once_with('~/.heyu.cert')
        mock_SafeConfigParser.assert_called_once_with()
        cp.read.assert_called_once_with('/home/dir/.heyu.cert')
        cp.items.assert_called_once_with('test')
        mock_TendrilPartial.assert_called_once_with(
            ssl.wrap_socket, keyfile='key', certfile='cert', ca_certs='ca',
            server_side=False, cert_reqs=ssl.CERT_REQUIRED,
            ssl_version=ssl.PROTOCOL_TLSv1)

    @mock.patch('os.path.expanduser', return_value='/home/dir/.heyu.cert')
    @mock.patch('ConfigParser.SafeConfigParser', return_value=mock.Mock(**{
        'read.return_value': ['/home/dir/.heyu.cert'],
        'items.return_value': [
            ('cafile', 'ca'),
            ('keyfile', 'key'),
            ('certfile', 'cert'),
        ],
    }))
    @mock.patch('tendril.TendrilPartial', return_value='wrapper')
    def test_server(self, mock_TendrilPartial, mock_SafeConfigParser,
                    mock_expanduser):
        cp = mock_SafeConfigParser.return_value

        result = util.cert_wrapper(None, 'test', True)

        self.assertEqual(result, 'wrapper')
        mock_expanduser.assert_called_once_with('~/.heyu.cert')
        mock_SafeConfigParser.assert_called_once_with()
        cp.read.assert_called_once_with('/home/dir/.heyu.cert')
        cp.items.assert_called_once_with('test')
        mock_TendrilPartial.assert_called_once_with(
            ssl.wrap_socket, keyfile='key', certfile='cert', ca_certs='ca',
            server_side=True, cert_reqs=ssl.CERT_REQUIRED,
            ssl_version=ssl.PROTOCOL_TLSv1)

    @mock.patch('os.path.expanduser', return_value='/home/dir/.heyu.cert')
    @mock.patch('ConfigParser.SafeConfigParser', return_value=mock.Mock(**{
        'read.return_value': ['/home/dir/.heyu.cert'],
        'items.return_value': [
            ('cafile', 'ca'),
            ('keyfile', 'key'),
            ('certfile', 'cert'),
        ],
    }))
    @mock.patch('tendril.TendrilPartial', return_value='wrapper')
    def test_alt_conf(self, mock_TendrilPartial, mock_SafeConfigParser,
                      mock_expanduser):
        cp = mock_SafeConfigParser.return_value

        result = util.cert_wrapper('alt_conf', 'test')

        self.assertEqual(result, 'wrapper')
        mock_expanduser.assert_called_once_with('alt_conf')
        mock_SafeConfigParser.assert_called_once_with()
        cp.read.assert_called_once_with('/home/dir/.heyu.cert')
        cp.items.assert_called_once_with('test')
        mock_TendrilPartial.assert_called_once_with(
            ssl.wrap_socket, keyfile='key', certfile='cert', ca_certs='ca',
            server_side=False, cert_reqs=ssl.CERT_REQUIRED,
            ssl_version=ssl.PROTOCOL_TLSv1)

    @mock.patch('os.path.expanduser', return_value='/home/dir/.heyu.cert')
    @mock.patch('ConfigParser.SafeConfigParser', return_value=mock.Mock(**{
        'read.return_value': ['/home/dir/.heyu.cert'],
        'items.return_value': [
            ('cafile', 'ca'),
            ('keyfile', 'key'),
            ('certfile', 'cert'),
        ],
    }))
    @mock.patch('tendril.TendrilPartial', return_value='wrapper')
    def test_alt_profile(self, mock_TendrilPartial, mock_SafeConfigParser,
                         mock_expanduser):
        cp = mock_SafeConfigParser.return_value

        result = util.cert_wrapper('alt_conf[alt_profile]', 'test')

        self.assertEqual(result, 'wrapper')
        mock_expanduser.assert_called_once_with('alt_conf')
        mock_SafeConfigParser.assert_called_once_with()
        cp.read.assert_called_once_with('/home/dir/.heyu.cert')
        cp.items.assert_called_once_with('alt_profile')
        mock_TendrilPartial.assert_called_once_with(
            ssl.wrap_socket, keyfile='key', certfile='cert', ca_certs='ca',
            server_side=False, cert_reqs=ssl.CERT_REQUIRED,
            ssl_version=ssl.PROTOCOL_TLSv1)

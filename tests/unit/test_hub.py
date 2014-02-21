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

import signal
import unittest

import mock

from heyu import hub


class TestException(Exception):
    pass


class HubServerTest(unittest.TestCase):
    @mock.patch('tendril.get_manager', side_effect=lambda a, b: b)
    @mock.patch('gevent.signal')
    def test_init_basic(self, mock_signal, mock_get_manager):
        result = hub.HubServer([])

        self.assertEqual({}, result._subscribers)
        self.assertEqual({}, result._listeners)
        self.assertEqual(False, result._running)
        self.assertFalse(mock_get_manager.called)
        mock_signal.assert_has_calls([
            mock.call(signal.SIGINT, result.stop),
            mock.call(signal.SIGTERM, result.stop),
            mock.call(signal.SIGUSR1, result.shutdown),
        ])

    @mock.patch('tendril.get_manager', side_effect=lambda a, b: b)
    @mock.patch('gevent.signal')
    def test_init_failusr1(self, mock_signal, mock_get_manager):
        def fake_signal(num, handler):
            if num == signal.SIGUSR1:
                raise TestException('test')
        mock_signal.side_effect = fake_signal

        result = hub.HubServer([])

        self.assertEqual({}, result._subscribers)
        self.assertEqual({}, result._listeners)
        self.assertEqual(False, result._running)
        self.assertFalse(mock_get_manager.called)
        mock_signal.assert_has_calls([
            mock.call(signal.SIGINT, result.stop),
            mock.call(signal.SIGTERM, result.stop),
            mock.call(signal.SIGUSR1, result.shutdown),
        ])

    @mock.patch('tendril.get_manager', side_effect=lambda a, b: b)
    @mock.patch('gevent.signal')
    def test_init_endpoints(self, mock_signal, mock_get_manager):
        result = hub.HubServer(['ep1', 'ep2', 'ep3'])

        self.assertEqual({}, result._subscribers)
        self.assertEqual({
            'ep1': 'ep1',
            'ep2': 'ep2',
            'ep3': 'ep3',
        }, result._listeners)
        self.assertEqual(False, result._running)
        mock_get_manager.assert_has_calls([
            mock.call('tcp', 'ep1'),
            mock.call('tcp', 'ep2'),
            mock.call('tcp', 'ep3'),
        ], any_order=True)
        mock_signal.assert_has_calls([
            mock.call(signal.SIGINT, result.stop),
            mock.call(signal.SIGTERM, result.stop),
            mock.call(signal.SIGUSR1, result.shutdown),
        ])

    @mock.patch.object(hub.HubServer, '__init__', return_value=None)
    @mock.patch.object(hub, 'HubApplication', return_value='app')
    def test_acceptor(self, mock_HubApplication, mock_init):
        server = hub.HubServer()

        result = server._acceptor('tendril')

        self.assertEqual(result, 'app')
        mock_HubApplication.assert_called_once_with('tendril', server)

    @mock.patch.object(hub.HubServer, '__init__', return_value=None)
    @mock.patch('heyu.util.cert_wrapper', return_value='wrapper')
    def test_start_running(self, mock_cert_wrapper, mock_init):
        server = hub.HubServer()
        server._listeners = {
            'a': mock.Mock(),
            'b': mock.Mock(),
            'c': mock.Mock(),
        }
        server._running = True

        self.assertRaises(ValueError, server.start)
        self.assertFalse(mock_cert_wrapper.called)

    @mock.patch.object(hub.HubServer, '__init__', return_value=None)
    @mock.patch('heyu.util.cert_wrapper', return_value='wrapper')
    def test_start_basic(self, mock_cert_wrapper, mock_init):
        server = hub.HubServer()
        server._listeners = {
            'a': mock.Mock(),
            'b': mock.Mock(),
            'c': mock.Mock(),
        }
        server._running = False

        server.start()

        self.assertEqual(True, server._running)
        mock_cert_wrapper.assert_called_once_with(None, 'hub', secure=True)
        for manager in server._listeners.values():
            manager.start.assert_called_once_with(server._acceptor, 'wrapper')

    @mock.patch.object(hub.HubServer, '__init__', return_value=None)
    @mock.patch('heyu.util.cert_wrapper', return_value='wrapper')
    def test_start_nolisteners(self, mock_cert_wrapper, mock_init):
        server = hub.HubServer()
        server._listeners = {}
        server._running = False

        server.start()

        self.assertEqual(True, server._running)
        mock_cert_wrapper.assert_called_once_with(None, 'hub', secure=True)
        for manager in server._listeners.values():
            manager.start.assert_called_once_with(server._acceptor, 'wrapper')

    @mock.patch.object(hub.HubServer, '__init__', return_value=None)
    def test_stop_notrunning(self, mock_init):
        server = hub.HubServer()
        server._listeners = {
            'a': mock.Mock(),
            'b': mock.Mock(),
            'c': mock.Mock(),
        }
        server._subscribers = {
            'a': (mock.Mock(), 0),
            'b': (mock.Mock(), 1),
            'c': (mock.Mock(), 2),
        }
        server._running = False

        server.stop()

        for manager in server._listeners.values():
            self.assertFalse(manager.stop.called)
        for client, _version in server._subscribers.values():
            self.assertFalse(client.disconnect.called)

    @mock.patch.object(hub.HubServer, '__init__', return_value=None)
    def test_stop_basic(self, mock_init):
        server = hub.HubServer()
        server._listeners = {
            'a': mock.Mock(),
            'b': mock.Mock(),
            'c': mock.Mock(),
        }
        server._subscribers = {
            'a': (mock.Mock(), 0),
            'b': (mock.Mock(), 1),
            'c': (mock.Mock(), 2),
        }
        server._running = True

        server.stop()

        self.assertEqual(False, server._running)
        for manager in server._listeners.values():
            manager.stop.assert_called_once_with()
        for client, _version in server._subscribers.values():
            client.disconnect.assert_called_once_with()

    @mock.patch.object(hub.HubServer, '__init__', return_value=None)
    def test_stop_empty(self, mock_init):
        server = hub.HubServer()
        server._listeners = {}
        server._subscribers = {}
        server._running = True

        server.stop()

        self.assertEqual(False, server._running)

    @mock.patch.object(hub.HubServer, '__init__', return_value=None)
    def test_shutdown_notrunning(self, mock_init):
        subscribers = {
            'a': (mock.Mock(), 0),
            'b': (mock.Mock(), 1),
            'c': (mock.Mock(), 2),
        }
        server = hub.HubServer()
        server._listeners = {
            'a': mock.Mock(),
            'b': mock.Mock(),
            'c': mock.Mock(),
        }
        server._subscribers = subscribers
        server._running = False

        server.shutdown()

        for manager in server._listeners.values():
            self.assertFalse(manager.shutdown.called)
        self.assertEqual(subscribers, server._subscribers)

    @mock.patch.object(hub.HubServer, '__init__', return_value=None)
    def test_shutdown_basic(self, mock_init):
        subscribers = {
            'a': (mock.Mock(), 0),
            'b': (mock.Mock(), 1),
            'c': (mock.Mock(), 2),
        }
        server = hub.HubServer()
        server._listeners = {
            'a': mock.Mock(),
            'b': mock.Mock(),
            'c': mock.Mock(),
        }
        server._subscribers = subscribers
        server._running = True

        server.shutdown()

        self.assertEqual(False, server._running)
        for manager in server._listeners.values():
            manager.shutdown.assert_called_once_with()
        self.assertEqual({}, server._subscribers)

    @mock.patch.object(hub.HubServer, '__init__', return_value=None)
    def test_shutdown_empty(self, mock_init):
        server = hub.HubServer()
        server._listeners = {}
        server._subscribers = {
            'a': (mock.Mock(), 0),
            'b': (mock.Mock(), 1),
            'c': (mock.Mock(), 2),
        }
        server._running = True

        server.shutdown()

        self.assertEqual(False, server._running)
        self.assertEqual({}, server._subscribers)

    @mock.patch.object(hub.HubServer, '__init__', return_value=None)
    def test_subscribe(self, mock_init):
        client = mock.Mock()
        server = hub.HubServer()
        server._subscribers = {}

        server.subscribe(client, 1)

        self.assertEqual({
            id(client): (client, 1),
        }, server._subscribers)

    @mock.patch.object(hub.HubServer, '__init__', return_value=None)
    def test_unsubscribe_unsubscribed(self, mock_init):
        client1 = mock.Mock()
        client2 = mock.Mock()
        server = hub.HubServer()
        server._subscribers = {
            id(client1): (client1, 0),
        }

        server.unsubscribe(client2)

        self.assertEqual({
            id(client1): (client1, 0),
        }, server._subscribers)

    @mock.patch.object(hub.HubServer, '__init__', return_value=None)
    def test_unsubscribe_subscribed(self, mock_init):
        client1 = mock.Mock()
        client2 = mock.Mock()
        server = hub.HubServer()
        server._subscribers = {
            id(client1): (client1, 0),
            id(client2): (client2, 0),
        }

        server.unsubscribe(client2)

        self.assertEqual({
            id(client1): (client1, 0),
        }, server._subscribers)

    @mock.patch.object(hub.HubServer, '__init__', return_value=None)
    def test_submit_empty(self, mock_init):
        msg = mock.Mock(**{'to_frame.side_effect': lambda x: 'version %d' % x})
        server = hub.HubServer()
        server._subscribers = {}

        server.submit(msg)

        self.assertFalse(msg.to_frame.called)

    @mock.patch.object(hub.HubServer, '__init__', return_value=None)
    def test_submit(self, mock_init):
        def fake_to_frame(version):
            if version > 2:
                raise TestException('version too high')
            return 'version %d' % version
        msg = mock.Mock(**{'to_frame.side_effect': fake_to_frame})
        server = hub.HubServer()
        server._subscribers = {
            'a': (mock.Mock(), 0),
            'b': (mock.Mock(), 1),
            'c': (mock.Mock(), 2),
            'd': (mock.Mock(), 3),
            'e': (mock.Mock(), 4),
        }

        server.submit(msg)

        msg.to_frame.assert_has_calls([
            mock.call(0),
            mock.call(1),
            mock.call(2),
            mock.call(3),
            mock.call(4),
        ], any_order=True)
        for client, version in server._subscribers.values():
            if version > 2:
                self.assertFalse(client.send_frame.called)
            else:
                client.send_frame.assert_called_once_with(
                    'version %d' % version)

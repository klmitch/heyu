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

from heyu import notifier
from heyu import util


class TestException(Exception):
    pass


class NotifierServerTest(unittest.TestCase):
    def _signal_test(self, notifier_server, mock_signal):
        signals = [
            mock.call(signal.SIGINT, notifier_server.stop),
            mock.call(signal.SIGTERM, notifier_server.stop),
        ]
        if hasattr(signal, 'SIGUSR1'):
            signals.append(mock.call(signal.SIGUSR1, notifier_server.shutdown))
        mock_signal.assert_has_calls(signals)
        self.assertEqual(len(signals), mock_signal.call_count)

    @mock.patch('sys.argv', ['/bin/notifier.py'])
    @mock.patch('tendril.get_manager', return_value='manager')
    @mock.patch('gevent.signal')
    @mock.patch('uuid.uuid4', return_value='some-uuid')
    @mock.patch('gevent.event.Event', return_value='event')
    @mock.patch.object(util, 'cert_wrapper', return_value='wrapper')
    @mock.patch.object(util, 'outgoing_endpoint', return_value='endpoint')
    def test_init_basic(self, mock_outgoing_endpoint, mock_cert_wrapper,
                        mock_Event, mock_uuid4, mock_signal, mock_get_manager):
        result = notifier.NotifierServer('hub')

        self.assertEqual('hub', result._hub)
        self.assertEqual('manager', result._manager)
        self.assertEqual('wrapper', result._wrapper)
        self.assertEqual('notifier.py', result._app_name)
        self.assertEqual('some-uuid', result._app_id)
        self.assertEqual(None, result._hub_app)
        self.assertEqual([], result._notifications)
        self.assertEqual('event', result._notify_event)
        mock_outgoing_endpoint.assert_called_once_with('hub')
        mock_get_manager.assert_called_once_with('tcp', 'endpoint')
        mock_cert_wrapper.assert_called_once_with(
            None, 'notifier', secure=True)
        self._signal_test(result, mock_signal)

    @mock.patch('sys.argv', ['/bin/notifier.py'])
    @mock.patch('tendril.get_manager', return_value='manager')
    @mock.patch('gevent.signal')
    @mock.patch('uuid.uuid4', return_value='some-uuid')
    @mock.patch('gevent.event.Event', return_value='event')
    @mock.patch.object(util, 'cert_wrapper', return_value='wrapper')
    @mock.patch.object(util, 'outgoing_endpoint', return_value='endpoint')
    def test_init_alt(self, mock_outgoing_endpoint, mock_cert_wrapper,
                      mock_Event, mock_uuid4, mock_signal, mock_get_manager):
        result = notifier.NotifierServer('hub', 'cert_conf', False, 'app',
                                         'app-uuid')

        self.assertEqual('hub', result._hub)
        self.assertEqual('manager', result._manager)
        self.assertEqual('wrapper', result._wrapper)
        self.assertEqual('app', result._app_name)
        self.assertEqual('app-uuid', result._app_id)
        self.assertEqual(None, result._hub_app)
        self.assertEqual([], result._notifications)
        self.assertEqual('event', result._notify_event)
        mock_outgoing_endpoint.assert_called_once_with('hub')
        mock_get_manager.assert_called_once_with('tcp', 'endpoint')
        mock_cert_wrapper.assert_called_once_with(
            'cert_conf', 'notifier', secure=False)
        self._signal_test(result, mock_signal)

    @mock.patch.object(notifier.NotifierServer, '__init__', return_value=None)
    @mock.patch.object(notifier.NotifierServer, 'start')
    def test_iter_running(self, mock_start, mock_init):
        server = notifier.NotifierServer()
        server._hub_app = 'application'

        result = iter(server)

        self.assertEqual(server, result)
        self.assertFalse(mock_start.called)

    @mock.patch.object(notifier.NotifierServer, '__init__', return_value=None)
    @mock.patch.object(notifier.NotifierServer, 'start')
    def test_iter_nonrunning(self, mock_start, mock_init):
        server = notifier.NotifierServer()
        server._hub_app = None

        result = iter(server)

        self.assertEqual(server, result)
        mock_start.assert_called_once_with()

    @mock.patch.object(notifier.NotifierServer, '__init__', return_value=None)
    @mock.patch('sys.exit', side_effect=TestException())
    def test_next_notification(self, mock_exit, mock_init):
        server = notifier.NotifierServer()
        server._notifications = ['notification']
        server._notify_event = mock.Mock()
        server._hub_app = None

        result = server.next()

        self.assertEqual('notification', result)
        self.assertEqual(0, len(server._notify_event.method_calls))

    @mock.patch.object(notifier.NotifierServer, '__init__', return_value=None)
    @mock.patch('sys.exit', side_effect=TestException())
    def test_next_exit(self, mock_exit, mock_init):
        server = notifier.NotifierServer()
        server._notifications = [None]
        server._notify_event = mock.Mock()
        server._hub_app = None

        self.assertRaises(TestException, server.next)
        mock_exit.assert_called_once_with()
        self.assertEqual(0, len(server._notify_event.method_calls))

    @mock.patch.object(notifier.NotifierServer, '__init__', return_value=None)
    @mock.patch('sys.exit', side_effect=TestException())
    def test_next_empty_stop(self, mock_exit, mock_init):
        server = notifier.NotifierServer()
        server._notifications = []
        server._notify_event = mock.Mock()
        server._hub_app = None

        self.assertRaises(StopIteration, server.next)
        server._notify_event.assert_has_calls([
            mock.call.clear(),
        ])
        self.assertEqual(1, len(server._notify_event.method_calls))

    @mock.patch.object(notifier.NotifierServer, '__init__', return_value=None)
    @mock.patch('sys.exit', side_effect=TestException())
    def test_next_empty_loop(self, mock_exit, mock_init):
        server = notifier.NotifierServer()
        server._notifications = []
        server._notify_event = mock.Mock()
        server._hub_app = 'app'

        def fake_wait():
            server._notifications.append('waited')
        server._notify_event.wait.side_effect = fake_wait

        result = server.next()

        self.assertEqual('waited', result)
        server._notify_event.assert_has_calls([
            mock.call.clear(),
            mock.call.wait(),
        ])
        self.assertEqual(2, len(server._notify_event.method_calls))

    @mock.patch.object(notifier.NotifierServer, '__init__', return_value=None)
    @mock.patch.object(notifier, 'NotifierApplication', return_value='app')
    def test_acceptor(self, mock_NotifierApplication, mock_init):
        server = notifier.NotifierServer()
        server._hub_app = True
        server._app_name = 'app_name'
        server._app_id = 'app_id'

        result = server._acceptor('tendril')

        self.assertEqual('app', result)
        mock_NotifierApplication.assert_called_once_with(
            'tendril', server, 'app_name', 'app_id')

    @mock.patch.object(notifier.NotifierServer, '__init__', return_value=None)
    def test_start_running(self, mock_init):
        server = notifier.NotifierServer()
        server._hub_app = 'running'
        server._manager = mock.Mock()
        server._hub = 'hub'
        server._wrapper = 'wrapper'

        self.assertRaises(ValueError, server.start)
        self.assertEqual('running', server._hub_app)
        self.assertEqual(0, len(server._manager.method_calls))

    @mock.patch.object(notifier.NotifierServer, '__init__', return_value=None)
    def test_start_stopped(self, mock_init):
        server = notifier.NotifierServer()
        server._hub_app = None
        server._manager = mock.Mock()
        server._hub = 'hub'
        server._wrapper = 'wrapper'

        server.start()

        self.assertEqual(True, server._hub_app)
        server._manager.assert_has_calls([
            mock.call.start(),
            mock.call.connect('hub', server._acceptor, 'wrapper'),
        ])
        self.assertEqual(2, len(server._manager.method_calls))

    @mock.patch.object(notifier.NotifierServer, '__init__', return_value=None)
    def test_stop_stopped(self, mock_init):
        server = notifier.NotifierServer()
        server._hub_app = None
        server._manager = mock.Mock()
        server._notifications = []
        server._notify_event = mock.Mock()

        server.stop()

        self.assertEqual(None, server._hub_app)
        self.assertEqual([], server._notifications)
        self.assertEqual(0, len(server._manager.method_calls))
        self.assertEqual(0, len(server._notify_event.method_calls))

    @mock.patch.object(notifier.NotifierServer, '__init__', return_value=None)
    def test_stop_simple(self, mock_init):
        app = mock.Mock()
        server = notifier.NotifierServer()
        server._hub_app = app
        server._manager = mock.Mock()
        server._notifications = []
        server._notify_event = mock.Mock()

        server.stop()

        self.assertEqual(None, server._hub_app)
        self.assertEqual([], server._notifications)
        server._manager.stop.assert_called_once_with()
        self.assertEqual(1, len(server._manager.method_calls))
        app.disconnect.assert_called_once_with()
        self.assertEqual(1, len(app.method_calls))
        server._notify_event.set.assert_called_once_with()
        self.assertEqual(1, len(server._notify_event.method_calls))

    @mock.patch.object(notifier.NotifierServer, '__init__', return_value=None)
    def test_stop_connecting(self, mock_init):
        server = notifier.NotifierServer()
        server._hub_app = True
        server._manager = mock.Mock()
        server._notifications = []
        server._notify_event = mock.Mock()

        server.stop()

        self.assertEqual(None, server._hub_app)
        self.assertEqual([], server._notifications)
        server._manager.stop.assert_called_once_with()
        self.assertEqual(1, len(server._manager.method_calls))
        server._notify_event.set.assert_called_once_with()
        self.assertEqual(1, len(server._notify_event.method_calls))

    @mock.patch.object(notifier.NotifierServer, '__init__', return_value=None)
    def test_stop_sentinel(self, mock_init):
        app = mock.Mock()
        server = notifier.NotifierServer()
        server._hub_app = app
        server._manager = mock.Mock()
        server._notifications = []
        server._notify_event = mock.Mock()

        server.stop('signal', 'arguments')

        self.assertEqual(None, server._hub_app)
        self.assertEqual([None], server._notifications)
        server._manager.stop.assert_called_once_with()
        self.assertEqual(1, len(server._manager.method_calls))
        app.disconnect.assert_called_once_with()
        self.assertEqual(1, len(app.method_calls))
        server._notify_event.set.assert_called_once_with()
        self.assertEqual(1, len(server._notify_event.method_calls))

    @mock.patch.object(notifier.NotifierServer, '__init__', return_value=None)
    def test_shutdown_stopped(self, mock_init):
        server = notifier.NotifierServer()
        server._hub_app = None
        server._manager = mock.Mock()
        server._notifications = []
        server._notify_event = mock.Mock()

        server.shutdown()

        self.assertEqual(None, server._hub_app)
        self.assertEqual([], server._notifications)
        self.assertEqual(0, len(server._manager.method_calls))
        self.assertEqual(0, len(server._notify_event.method_calls))

    @mock.patch.object(notifier.NotifierServer, '__init__', return_value=None)
    def test_shutdown_running(self, mock_init):
        server = notifier.NotifierServer()
        server._hub_app = 'running'
        server._manager = mock.Mock()
        server._notifications = []
        server._notify_event = mock.Mock()

        server.shutdown()

        self.assertEqual(None, server._hub_app)
        self.assertEqual([None], server._notifications)
        server._manager.shutdown.assert_called_once_with()
        self.assertEqual(1, len(server._manager.method_calls))
        server._notify_event.set.assert_called_once_with()
        self.assertEqual(1, len(server._notify_event.method_calls))

    @mock.patch.object(notifier.NotifierServer, '__init__', return_value=None)
    def test_notify(self, mock_init):
        server = notifier.NotifierServer()
        server._notifications = []
        server._notify_event = mock.Mock()

        server.notify('notification')

        self.assertEqual(['notification'], server._notifications)
        server._notify_event.set.assert_called_once_with()
        self.assertEqual(1, len(server._notify_event.method_calls))

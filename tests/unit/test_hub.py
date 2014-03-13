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
from heyu import util


class TestException(Exception):
    pass


class HubServerTest(unittest.TestCase):
    def _signal_test(self, hub_server, mock_signal):
        signals = [
            mock.call(signal.SIGINT, hub_server.stop),
            mock.call(signal.SIGTERM, hub_server.stop),
        ]
        if hasattr(signal, 'SIGUSR1'):
            signals.append(mock.call(signal.SIGUSR1, hub_server.shutdown))
        mock_signal.assert_has_calls(signals)
        self.assertEqual(len(signals), mock_signal.call_count)

    @mock.patch('tendril.get_manager', side_effect=lambda a, b: b)
    @mock.patch('gevent.signal')
    def test_init_basic(self, mock_signal, mock_get_manager):
        result = hub.HubServer([])

        self.assertEqual({}, result._subscribers)
        self.assertEqual({}, result._listeners)
        self.assertEqual(False, result._running)
        self.assertFalse(mock_get_manager.called)
        self._signal_test(result, mock_signal)

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
        self._signal_test(result, mock_signal)

    @mock.patch.object(hub.HubServer, '__init__', return_value=None)
    @mock.patch.object(hub, 'HubApplication', return_value='app')
    def test_acceptor(self, mock_HubApplication, mock_init):
        server = hub.HubServer()

        result = server._acceptor('tendril')

        self.assertEqual(result, 'app')
        mock_HubApplication.assert_called_once_with('tendril', server)

    @mock.patch.object(hub.HubServer, '__init__', return_value=None)
    @mock.patch.object(util, 'cert_wrapper', return_value='wrapper')
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
    @mock.patch.object(util, 'cert_wrapper', return_value='wrapper')
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
        mock_cert_wrapper.assert_called_once_with(
            None, 'hub', server_side=True, secure=True)
        for manager in server._listeners.values():
            manager.start.assert_called_once_with(server._acceptor, 'wrapper')

    @mock.patch.object(hub.HubServer, '__init__', return_value=None)
    @mock.patch.object(util, 'cert_wrapper', return_value='wrapper')
    def test_start_nolisteners(self, mock_cert_wrapper, mock_init):
        server = hub.HubServer()
        server._listeners = {}
        server._running = False

        server.start()

        self.assertEqual(True, server._running)
        mock_cert_wrapper.assert_called_once_with(
            None, 'hub', server_side=True, secure=True)
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


class HubApplicationTest(unittest.TestCase):
    @mock.patch('tendril.Application.__init__', return_value=None)
    @mock.patch('tendril.COBSFramer', return_value='framer')
    @mock.patch('socket.getfqdn', return_value='fqdn')
    @mock.patch('socket.getnameinfo', return_value=('host', 1234))
    def test_init_localipv4(self, mock_getnameinfo, mock_getfqdn,
                            mock_COBSFramer, mock_init):
        parent = mock.Mock(addr=('127.0.0.1', 4321))

        app = hub.HubApplication(parent, 'server')

        self.assertEqual('server', app.server)
        self.assertEqual(False, app.persist)
        self.assertEqual('fqdn', app.hostname)
        mock_init.assert_called_once_with(parent)
        mock_COBSFramer.assert_called_once_with(True)
        self.assertEqual('framer', parent.framers)
        mock_getfqdn.assert_called_once_with()
        self.assertFalse(mock_getnameinfo.called)

    @mock.patch('tendril.Application.__init__', return_value=None)
    @mock.patch('tendril.COBSFramer', return_value='framer')
    @mock.patch('socket.getfqdn', return_value='fqdn')
    @mock.patch('socket.getnameinfo', return_value=('host', 1234))
    def test_init_localipv6(self, mock_getnameinfo, mock_getfqdn,
                            mock_COBSFramer, mock_init):
        parent = mock.Mock(addr=('::1', 4321))

        app = hub.HubApplication(parent, 'server')

        self.assertEqual('server', app.server)
        self.assertEqual(False, app.persist)
        self.assertEqual('fqdn', app.hostname)
        mock_init.assert_called_once_with(parent)
        mock_COBSFramer.assert_called_once_with(True)
        self.assertEqual('framer', parent.framers)
        mock_getfqdn.assert_called_once_with()
        self.assertFalse(mock_getnameinfo.called)

    @mock.patch('tendril.Application.__init__', return_value=None)
    @mock.patch('tendril.COBSFramer', return_value='framer')
    @mock.patch('socket.getfqdn', return_value='fqdn')
    @mock.patch('socket.getnameinfo', return_value=('host', 1234))
    def test_init_remote(self, mock_getnameinfo, mock_getfqdn,
                         mock_COBSFramer, mock_init):
        parent = mock.Mock(addr=('10.0.0.1', 4321))

        app = hub.HubApplication(parent, 'server')

        self.assertEqual('server', app.server)
        self.assertEqual(False, app.persist)
        self.assertEqual('host', app.hostname)
        mock_init.assert_called_once_with(parent)
        mock_COBSFramer.assert_called_once_with(True)
        self.assertEqual('framer', parent.framers)
        self.assertFalse(mock_getfqdn.called)
        mock_getnameinfo.assert_called_once_with(('10.0.0.1', 4321), 0)

    @mock.patch('tendril.Application.__init__', return_value=None)
    @mock.patch('tendril.COBSFramer', return_value='framer')
    @mock.patch('socket.getfqdn', return_value='fqdn')
    @mock.patch('socket.getnameinfo', side_effect=TestException('error'))
    def test_init_bad_resolve(self, mock_getnameinfo, mock_getfqdn,
                              mock_COBSFramer, mock_init):
        parent = mock.Mock(addr=('10.0.0.1', 4321))

        app = hub.HubApplication(parent, 'server')

        self.assertEqual('server', app.server)
        self.assertEqual(False, app.persist)
        self.assertEqual('10.0.0.1', app.hostname)
        mock_init.assert_called_once_with(parent)
        mock_COBSFramer.assert_called_once_with(True)
        self.assertEqual('framer', parent.framers)
        self.assertFalse(mock_getfqdn.called)
        mock_getnameinfo.assert_called_once_with(('10.0.0.1', 4321), 0)

    @mock.patch('heyu.protocol.Message', return_value=mock.Mock(**{
        'to_frame.return_value': 'some frame',
    }), **{'from_frame.side_effect': ValueError('failed to decode')})
    @mock.patch.object(hub.HubApplication, '__init__', return_value=None)
    @mock.patch.object(hub.HubApplication, 'send_frame')
    @mock.patch.object(hub.HubApplication, 'close')
    @mock.patch.object(hub.HubApplication, 'notify')
    @mock.patch.object(hub.HubApplication, 'subscribe')
    @mock.patch.object(hub.HubApplication, 'disconnect')
    def test_recv_frame_decodeerror(self, mock_disconnect, mock_subscribe,
                                    mock_notify, mock_close, mock_send_frame,
                                    mock_init, mock_Message):
        app = hub.HubApplication()

        app.recv_frame('test')

        mock_Message.from_frame.assert_called_once_with('test')
        mock_Message.assert_called_once_with(
            'error', reason='Failed to decode message: failed to decode')
        mock_Message.return_value.to_frame.assert_called_once_with()
        mock_send_frame.assert_called_once_with('some frame')
        mock_close.assert_called_once_with()
        self.assertFalse(mock_notify.called)
        self.assertFalse(mock_subscribe.called)
        self.assertFalse(mock_disconnect.called)

    @mock.patch('heyu.protocol.Message', return_value=mock.Mock(**{
        'to_frame.return_value': 'some frame',
    }), **{'from_frame.return_value': mock.Mock(msg_type='unknown')})
    @mock.patch.object(hub.HubApplication, '__init__', return_value=None)
    @mock.patch.object(hub.HubApplication, 'send_frame')
    @mock.patch.object(hub.HubApplication, 'close')
    @mock.patch.object(hub.HubApplication, 'notify')
    @mock.patch.object(hub.HubApplication, 'subscribe')
    @mock.patch.object(hub.HubApplication, 'disconnect')
    def test_recv_frame_unknownmsg(self, mock_disconnect, mock_subscribe,
                                   mock_notify, mock_close, mock_send_frame,
                                   mock_init, mock_Message):
        app = hub.HubApplication()

        app.recv_frame('test')

        mock_Message.from_frame.assert_called_once_with('test')
        mock_Message.assert_called_once_with(
            'error', reason='Unknown message type "unknown"')
        mock_Message.return_value.to_frame.assert_called_once_with()
        mock_send_frame.assert_called_once_with('some frame')
        mock_close.assert_called_once_with()
        self.assertFalse(mock_notify.called)
        self.assertFalse(mock_subscribe.called)
        self.assertFalse(mock_disconnect.called)

    @mock.patch('heyu.protocol.Message', return_value=mock.Mock(**{
        'to_frame.return_value': 'some frame',
    }), **{'from_frame.return_value': mock.Mock(msg_type='notify')})
    @mock.patch.object(hub.HubApplication, '__init__', return_value=None)
    @mock.patch.object(hub.HubApplication, 'send_frame')
    @mock.patch.object(hub.HubApplication, 'close')
    @mock.patch.object(hub.HubApplication, 'notify')
    @mock.patch.object(hub.HubApplication, 'subscribe')
    @mock.patch.object(hub.HubApplication, 'disconnect')
    def test_recv_frame_notify(self, mock_disconnect, mock_subscribe,
                               mock_notify, mock_close, mock_send_frame,
                               mock_init, mock_Message):
        app = hub.HubApplication()

        app.recv_frame('test')

        mock_Message.from_frame.assert_called_once_with('test')
        self.assertFalse(mock_Message.called)
        self.assertFalse(mock_send_frame.called)
        self.assertFalse(mock_close.called)
        mock_notify.assert_called_once_with(
            mock_Message.from_frame.return_value)
        self.assertFalse(mock_subscribe.called)
        self.assertFalse(mock_disconnect.called)

    @mock.patch('heyu.protocol.Message', return_value=mock.Mock(**{
        'to_frame.return_value': 'some frame',
    }), **{'from_frame.return_value': mock.Mock(msg_type='subscribe')})
    @mock.patch.object(hub.HubApplication, '__init__', return_value=None)
    @mock.patch.object(hub.HubApplication, 'send_frame')
    @mock.patch.object(hub.HubApplication, 'close')
    @mock.patch.object(hub.HubApplication, 'notify')
    @mock.patch.object(hub.HubApplication, 'subscribe')
    @mock.patch.object(hub.HubApplication, 'disconnect')
    def test_recv_frame_subscribe(self, mock_disconnect, mock_subscribe,
                                  mock_notify, mock_close, mock_send_frame,
                                  mock_init, mock_Message):
        app = hub.HubApplication()

        app.recv_frame('test')

        mock_Message.from_frame.assert_called_once_with('test')
        self.assertFalse(mock_Message.called)
        self.assertFalse(mock_send_frame.called)
        self.assertFalse(mock_close.called)
        self.assertFalse(mock_notify.called)
        mock_subscribe.assert_called_once_with(
            mock_Message.from_frame.return_value)
        self.assertFalse(mock_disconnect.called)

    @mock.patch('heyu.protocol.Message', return_value=mock.Mock(**{
        'to_frame.return_value': 'some frame',
    }), **{'from_frame.return_value': mock.Mock(msg_type='goodbye')})
    @mock.patch.object(hub.HubApplication, '__init__', return_value=None)
    @mock.patch.object(hub.HubApplication, 'send_frame')
    @mock.patch.object(hub.HubApplication, 'close')
    @mock.patch.object(hub.HubApplication, 'notify')
    @mock.patch.object(hub.HubApplication, 'subscribe')
    @mock.patch.object(hub.HubApplication, 'disconnect')
    def test_recv_frame_goodbye(self, mock_disconnect, mock_subscribe,
                                mock_notify, mock_close, mock_send_frame,
                                mock_init, mock_Message):
        app = hub.HubApplication()

        app.recv_frame('test')

        mock_Message.from_frame.assert_called_once_with('test')
        self.assertFalse(mock_Message.called)
        self.assertFalse(mock_send_frame.called)
        self.assertFalse(mock_close.called)
        self.assertFalse(mock_notify.called)
        self.assertFalse(mock_subscribe.called)
        mock_disconnect.assert_called_once_with()

    @mock.patch('uuid.uuid4', return_value='some-uuid')
    @mock.patch('heyu.protocol.Message')
    @mock.patch.object(hub.HubApplication, '__init__', return_value=None)
    @mock.patch.object(hub.HubApplication, 'send_frame')
    @mock.patch.object(hub.HubApplication, 'close')
    def test_notify_success(self, mock_close, mock_send_frame, mock_init,
                            mock_Message, mock_uuid4):
        msgs = {
            'notify': 'notification',
            'error': mock.Mock(**{'to_frame.return_value': 'error'}),
            'accepted': mock.Mock(**{'to_frame.return_value': 'accepted'}),
        }
        mock_Message.side_effect = lambda x, **kw: msgs[x]
        msg = mock.Mock(id=None, app_name='app', summary='summary',
                        body='body', urgency='urgency', category='category')
        app = hub.HubApplication()
        app.hostname = 'host'
        app.server = mock.Mock()
        app.persist = True

        app.notify(msg)

        mock_uuid4.assert_called_once_with()
        mock_Message.assert_has_calls([
            mock.call('notify', id='some-uuid', app_name='[host]app',
                      summary='summary', body='body', urgency='urgency',
                      category='category'),
            mock.call('accepted', id='some-uuid'),
        ])
        app.server.submit.assert_called_once_with('notification')
        self.assertFalse(msgs['error'].to_frame.called)
        msgs['accepted'].to_frame.assert_called_once_with()
        mock_send_frame.assert_called_once_with('accepted')
        self.assertFalse(mock_close.called)

    @mock.patch('uuid.uuid4', return_value='some-uuid')
    @mock.patch('heyu.protocol.Message')
    @mock.patch.object(hub.HubApplication, '__init__', return_value=None)
    @mock.patch.object(hub.HubApplication, 'send_frame')
    @mock.patch.object(hub.HubApplication, 'close')
    def test_notify_provided_id(self, mock_close, mock_send_frame, mock_init,
                                mock_Message, mock_uuid4):
        msgs = {
            'notify': 'notification',
            'error': mock.Mock(**{'to_frame.return_value': 'error'}),
            'accepted': mock.Mock(**{'to_frame.return_value': 'accepted'}),
        }
        mock_Message.side_effect = lambda x, **kw: msgs[x]
        msg = mock.Mock(id='my-id', app_name='app', summary='summary',
                        body='body', urgency='urgency', category='category')
        app = hub.HubApplication()
        app.hostname = 'host'
        app.server = mock.Mock()
        app.persist = True

        app.notify(msg)

        self.assertFalse(mock_uuid4.called)
        mock_Message.assert_has_calls([
            mock.call('notify', id='my-id', app_name='[host]app',
                      summary='summary', body='body', urgency='urgency',
                      category='category'),
            mock.call('accepted', id='my-id'),
        ])
        app.server.submit.assert_called_once_with('notification')
        self.assertFalse(msgs['error'].to_frame.called)
        msgs['accepted'].to_frame.assert_called_once_with()
        mock_send_frame.assert_called_once_with('accepted')
        self.assertFalse(mock_close.called)

    @mock.patch('uuid.uuid4', return_value='some-uuid')
    @mock.patch('heyu.protocol.Message')
    @mock.patch.object(hub.HubApplication, '__init__', return_value=None)
    @mock.patch.object(hub.HubApplication, 'send_frame')
    @mock.patch.object(hub.HubApplication, 'close')
    def test_notify_no_persist(self, mock_close, mock_send_frame, mock_init,
                               mock_Message, mock_uuid4):
        msgs = {
            'notify': 'notification',
            'error': mock.Mock(**{'to_frame.return_value': 'error'}),
            'accepted': mock.Mock(**{'to_frame.return_value': 'accepted'}),
        }
        mock_Message.side_effect = lambda x, **kw: msgs[x]
        msg = mock.Mock(id=None, app_name='app', summary='summary',
                        body='body', urgency='urgency', category='category')
        app = hub.HubApplication()
        app.hostname = 'host'
        app.server = mock.Mock()
        app.persist = False

        app.notify(msg)

        mock_uuid4.assert_called_once_with()
        mock_Message.assert_has_calls([
            mock.call('notify', id='some-uuid', app_name='[host]app',
                      summary='summary', body='body', urgency='urgency',
                      category='category'),
            mock.call('accepted', id='some-uuid'),
        ])
        app.server.submit.assert_called_once_with('notification')
        self.assertFalse(msgs['error'].to_frame.called)
        msgs['accepted'].to_frame.assert_called_once_with()
        mock_send_frame.assert_called_once_with('accepted')
        mock_close.assert_called_once_with()

    @mock.patch('uuid.uuid4', return_value='some-uuid')
    @mock.patch('heyu.protocol.Message')
    @mock.patch.object(hub.HubApplication, '__init__', return_value=None)
    @mock.patch.object(hub.HubApplication, 'send_frame')
    @mock.patch.object(hub.HubApplication, 'close')
    def test_notify_failure(self, mock_close, mock_send_frame, mock_init,
                            mock_Message, mock_uuid4):
        msgs = {
            'notify': 'notification',
            'error': mock.Mock(**{'to_frame.return_value': 'error'}),
            'accepted': mock.Mock(**{'to_frame.return_value': 'accepted'}),
        }
        mock_Message.side_effect = lambda x, **kw: msgs[x]
        msg = mock.Mock(id=None, app_name='app', summary='summary',
                        body='body', urgency='urgency', category='category')
        app = hub.HubApplication()
        app.hostname = 'host'
        app.server = mock.Mock(**{
            'submit.side_effect': TestException('failed'),
        })
        app.persist = True

        app.notify(msg)

        mock_uuid4.assert_called_once_with()
        mock_Message.assert_has_calls([
            mock.call('notify', id='some-uuid', app_name='[host]app',
                      summary='summary', body='body', urgency='urgency',
                      category='category'),
            mock.call('error', reason='Failed to submit notification: failed'),
        ])
        app.server.submit.assert_called_once_with('notification')
        msgs['error'].to_frame.assert_called_once_with()
        self.assertFalse(msgs['accepted'].to_frame.called)
        mock_send_frame.assert_called_once_with('error')
        self.assertFalse(mock_close.called)

    @mock.patch('heyu.protocol.Message', return_value=mock.Mock(**{
        'to_frame.return_value': 'frame',
    }))
    @mock.patch.object(hub.HubApplication, '__init__', return_value=None)
    @mock.patch.object(hub.HubApplication, 'send_frame')
    @mock.patch.object(hub.HubApplication, 'close')
    def test_subscribe_success(self, mock_close, mock_send_frame, mock_init,
                               mock_Message):
        msg = mock.Mock(version=1)
        app = hub.HubApplication()
        app.persist = False
        app.server = mock.Mock()

        app.subscribe(msg)

        app.server.subscribe.assert_called_once_with(app, 1)
        mock_Message.assert_called_once_with('subscribed')
        mock_Message.return_value.to_frame.assert_called_once_with()
        mock_send_frame.assert_called_once_with('frame')
        self.assertFalse(mock_close.called)
        self.assertEqual(True, app.persist)

    @mock.patch('heyu.protocol.Message', return_value=mock.Mock(**{
        'to_frame.return_value': 'frame',
    }))
    @mock.patch.object(hub.HubApplication, '__init__', return_value=None)
    @mock.patch.object(hub.HubApplication, 'send_frame')
    @mock.patch.object(hub.HubApplication, 'close')
    def test_subscribe_failure(self, mock_close, mock_send_frame, mock_init,
                               mock_Message):
        msg = mock.Mock(version=1)
        app = hub.HubApplication()
        app.persist = False
        app.server = mock.Mock(**{
            'subscribe.side_effect': TestException('failed'),
        })

        app.subscribe(msg)

        app.server.subscribe.assert_called_once_with(app, 1)
        mock_Message.assert_called_once_with(
            'error', reason='Failed to subscribe: failed')
        mock_Message.return_value.to_frame.assert_called_once_with()
        mock_send_frame.assert_called_once_with('frame')
        mock_close.assert_called_once_with()
        self.assertEqual(False, app.persist)

    @mock.patch('heyu.protocol.Message', return_value=mock.Mock(**{
        'to_frame.return_value': 'frame',
    }))
    @mock.patch.object(hub.HubApplication, '__init__', return_value=None)
    @mock.patch.object(hub.HubApplication, 'send_frame')
    @mock.patch.object(hub.HubApplication, 'close')
    def test_disconnect_success(self, mock_close, mock_send_frame, mock_init,
                                mock_Message):
        app = hub.HubApplication()
        app.server = mock.Mock()

        app.disconnect()

        app.server.unsubscribe.assert_called_once_with(app)
        mock_Message.assert_called_once_with('goodbye')
        mock_Message.return_value.to_frame.assert_called_once_with()
        mock_send_frame.assert_called_once_with('frame')
        mock_close.assert_called_once_with()

    @mock.patch('heyu.protocol.Message', return_value=mock.Mock(**{
        'to_frame.return_value': 'frame',
    }))
    @mock.patch.object(hub.HubApplication, '__init__', return_value=None)
    @mock.patch.object(hub.HubApplication, 'send_frame',
                       side_effect=TestException('test'))
    @mock.patch.object(hub.HubApplication, 'close')
    def test_disconnect_failure(self, mock_close, mock_send_frame, mock_init,
                                mock_Message):
        app = hub.HubApplication()
        app.server = mock.Mock()

        app.disconnect()

        app.server.unsubscribe.assert_called_once_with(app)
        mock_Message.assert_called_once_with('goodbye')
        mock_Message.return_value.to_frame.assert_called_once_with()
        mock_send_frame.assert_called_once_with('frame')
        mock_close.assert_called_once_with()

    @mock.patch.object(hub.HubApplication, '__init__', return_value=None)
    def test_closed(self, mock_init):
        app = hub.HubApplication()
        app.server = mock.Mock()

        app.closed(None)

        app.server.unsubscribe.assert_called_once_with(app)


class StartHubTest(unittest.TestCase):
    @mock.patch('gevent.wait')
    @mock.patch.object(hub, 'HubServer')
    def test_basic(self, mock_HubServer, mock_wait):
        hub.start_hub(['ep1', 'ep2', 'ep3'])

        mock_HubServer.assert_called_once_with(['ep1', 'ep2', 'ep3'])
        mock_HubServer.return_value.start.assert_called_once_with(None, True)
        mock_wait.assert_called_once_with()

    @mock.patch('gevent.wait')
    @mock.patch.object(hub, 'HubServer')
    def test_alts(self, mock_HubServer, mock_wait):
        hub.start_hub(['ep1', 'ep2', 'ep3'], 'cert_conf', False)

        mock_HubServer.assert_called_once_with(['ep1', 'ep2', 'ep3'])
        mock_HubServer.return_value.start.assert_called_once_with(
            'cert_conf', False)
        mock_wait.assert_called_once_with()


class NormalizeArgsTest(unittest.TestCase):
    @mock.patch('socket.has_ipv6', False)
    @mock.patch.object(util, 'parse_hub', side_effect=lambda x: x)
    @mock.patch.object(util, 'daemonize')
    def test_no_endpoints_v4(self, mock_daemonize, mock_parse_hub):
        args = mock.Mock(
            endpoints=[],
            daemon=True,
            debug=False,
            pid_file=None,
        )

        hub._normalize_args(args)

        self.assertEqual([('', util.HEYU_PORT)], args.endpoints)
        self.assertFalse(mock_parse_hub.called)
        mock_daemonize.assert_called_once_with(pidfile=None)

    @mock.patch('socket.has_ipv6', True)
    @mock.patch.object(util, 'parse_hub', side_effect=lambda x: x)
    @mock.patch.object(util, 'daemonize')
    def test_no_endpoints_v6(self, mock_daemonize, mock_parse_hub):
        args = mock.Mock(
            endpoints=[],
            daemon=True,
            debug=False,
            pid_file=None,
        )

        hub._normalize_args(args)

        self.assertEqual([('', util.HEYU_PORT), ('::', util.HEYU_PORT)],
                         args.endpoints)
        self.assertFalse(mock_parse_hub.called)
        mock_daemonize.assert_called_once_with(pidfile=None)

    @mock.patch('socket.has_ipv6', True)
    @mock.patch.object(util, 'parse_hub', side_effect=lambda x: (x, 1234))
    @mock.patch.object(util, 'daemonize')
    def test_with_endpoints(self, mock_daemonize, mock_parse_hub):
        args = mock.Mock(
            endpoints=['ep1', 'ep2', 'ep3'],
            daemon=True,
            debug=False,
            pid_file=None,
        )

        hub._normalize_args(args)

        self.assertEqual([('ep1', 1234), ('ep2', 1234), ('ep3', 1234)],
                         args.endpoints)
        mock_parse_hub.assert_has_calls([
            mock.call('ep1'),
            mock.call('ep2'),
            mock.call('ep3'),
        ])
        mock_daemonize.assert_called_once_with(pidfile=None)

    @mock.patch('socket.has_ipv6', True)
    @mock.patch.object(util, 'parse_hub', side_effect=lambda x: x)
    @mock.patch.object(util, 'daemonize')
    def test_daemonize_debug(self, mock_daemonize, mock_parse_hub):
        args = mock.Mock(
            endpoints=[],
            daemon=True,
            debug=True,
            pid_file=None,
        )

        hub._normalize_args(args)

        self.assertEqual([('', util.HEYU_PORT), ('::', util.HEYU_PORT)],
                         args.endpoints)
        self.assertFalse(mock_parse_hub.called)
        self.assertFalse(mock_daemonize.called)

    @mock.patch('socket.has_ipv6', True)
    @mock.patch.object(util, 'parse_hub', side_effect=lambda x: x)
    @mock.patch.object(util, 'daemonize')
    def test_daemonize_nodaemon(self, mock_daemonize, mock_parse_hub):
        args = mock.Mock(
            endpoints=[],
            daemon=False,
            debug=False,
            pid_file=None,
        )

        hub._normalize_args(args)

        self.assertEqual([('', util.HEYU_PORT), ('::', util.HEYU_PORT)],
                         args.endpoints)
        self.assertFalse(mock_parse_hub.called)
        self.assertFalse(mock_daemonize.called)

    @mock.patch('socket.has_ipv6', True)
    @mock.patch.object(util, 'parse_hub', side_effect=lambda x: x)
    @mock.patch.object(util, 'daemonize')
    def test_daemonize_pidfile(self, mock_daemonize, mock_parse_hub):
        args = mock.Mock(
            endpoints=[],
            daemon=True,
            debug=False,
            pid_file='/path/to/pid',
        )

        hub._normalize_args(args)

        self.assertEqual([('', util.HEYU_PORT), ('::', util.HEYU_PORT)],
                         args.endpoints)
        self.assertFalse(mock_parse_hub.called)
        mock_daemonize.assert_called_once_with(pidfile='/path/to/pid')

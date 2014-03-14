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

try:
    import pynotify
except ImportError:
    from heyu import fake_pynotify as pynotify

from heyu import fake_pynotify
from heyu import gtk
from heyu import protocol


class TestException(Exception):
    pass


class BackoffTest(unittest.TestCase):
    @mock.patch('time.time')
    @mock.patch('time.sleep')
    def test_function(self, mock_sleep, mock_time):
        mock_time.return_value = 123456789.1
        expected = [None, 1, 2, 4, 8, 16, 32, 64, 128, 256, 300, 300]

        gen = gtk.backoff(300, 30, 5)

        idx = 0
        for _dummy in gen:
            if expected[idx] is None:
                self.assertFalse(mock_sleep.called)
            else:
                mock_sleep.assert_called_once_with(expected[idx])

            # Reset the mock for the next loop around
            mock_sleep.reset_mock()

            # Need a halting condition, though
            idx += 1
            if idx >= len(expected):
                break

        # Now need to simulate success
        expected = range(300, -6, -6)
        idx = 0
        for _dummy in gen:
            mock_sleep.assert_called_once_with(expected[idx])

            # Reset the mock and update the time for the next loop
            # around
            mock_sleep.reset_mock()
            mock_time.return_value += 30.0

            # Need a halting condition, though
            idx += 1
            if idx >= len(expected):
                break


class GtkNotifierTest(unittest.TestCase):
    @mock.patch('heyu.notifications.NotificationServer',
                return_value=mock.MagicMock(app_name='app_name',
                                            app_id='app_id'))
    @mock.patch.object(pynotify, 'init')
    @mock.patch.object(pynotify, 'Notification')
    @mock.patch.object(gtk, 'backoff', return_value=range(1))
    def test_basic(self, mock_backoff, mock_Notification, mock_init,
                   mock_NotificationServer):
        mock_NotificationServer.return_value.__iter__.return_value = iter([
            mock.Mock(id='notify-1', urgency=protocol.URGENCY_LOW,
                      app_name='application-1', summary='summary-1',
                      body='body-1', category='cat-1'),
            mock.Mock(id='notify-2', urgency=protocol.URGENCY_NORMAL,
                      app_name='application-2', summary='summary-2',
                      body='body-2', category=None),
            mock.Mock(id='notify-3', urgency=protocol.URGENCY_CRITICAL,
                      app_name='application-3', summary='summary-3',
                      body='body-3', category='cat-3'),
        ])

        gtk.gtk_notifier('hub')

        mock_backoff.assert_called_once_with(300, 30, 5)
        mock_NotificationServer.assert_called_once_with('hub', None, True)
        mock_init.assert_called_once_with('app_name')
        mock_Notification.assert_has_calls([
            mock.call('Starting', 'app_name is starting up'),
            mock.call().set_category('network'),
            mock.call().set_urgency(protocol.URGENCY_LOW),
            mock.call().show(),
            mock.call('summary-1', 'body-1'),
            mock.call().set_category('cat-1'),
            mock.call().set_urgency(protocol.URGENCY_LOW),
            mock.call().show(),
            mock.call('summary-2', 'body-2'),
            mock.call().set_category(''),
            mock.call().set_urgency(protocol.URGENCY_NORMAL),
            mock.call().show(),
            mock.call('summary-3', 'body-3'),
            mock.call().set_category('cat-3'),
            mock.call().set_urgency(protocol.URGENCY_CRITICAL),
            mock.call().show(),
        ])

    @mock.patch('heyu.notifications.NotificationServer',
                return_value=mock.MagicMock(app_name='app_name',
                                            app_id='app_id'))
    @mock.patch.object(pynotify, 'init')
    @mock.patch.object(pynotify, 'Notification')
    @mock.patch.object(gtk, 'backoff', return_value=range(1))
    def test_replace(self, mock_backoff, mock_Notification, mock_init,
                     mock_NotificationServer):
        mock_NotificationServer.return_value.__iter__.return_value = iter([
            mock.Mock(id='app_id', urgency=protocol.URGENCY_NORMAL,
                      app_name='app_name', summary='summary-1',
                      body='body-1', category='cat-1'),
        ])

        gtk.gtk_notifier('hub')

        mock_backoff.assert_called_once_with(300, 30, 5)
        mock_NotificationServer.assert_called_once_with('hub', None, True)
        mock_init.assert_called_once_with('app_name')
        mock_Notification.assert_has_calls([
            mock.call('Starting', 'app_name is starting up'),
            mock.call().set_category('network'),
            mock.call().set_urgency(protocol.URGENCY_LOW),
            mock.call().show(),
            mock.call().update('summary-1', 'body-1'),
            mock.call().set_category('cat-1'),
            mock.call().set_urgency(protocol.URGENCY_NORMAL),
            mock.call().show(),
        ])

    @mock.patch('heyu.notifications.NotificationServer',
                return_value=mock.MagicMock(app_name='app_name',
                                            app_id='app_id'))
    @mock.patch.object(pynotify, 'init')
    @mock.patch.object(pynotify, 'Notification')
    @mock.patch.object(gtk, 'backoff', return_value=range(3))
    def test_retry(self, mock_backoff, mock_Notification, mock_init,
                   mock_NotificationServer):
        mock_NotificationServer.return_value.__iter__.side_effect = [
            iter([
                mock.Mock(id='notify-1', urgency=protocol.URGENCY_LOW,
                          app_name='application-1', summary='summary-1',
                          body='body-1', category='cat-1'),
            ]),
            iter([
                mock.Mock(id='notify-2', urgency=protocol.URGENCY_NORMAL,
                          app_name='application-2', summary='summary-2',
                          body='body-2', category=None),
            ]),
            iter([
                mock.Mock(id='notify-3', urgency=protocol.URGENCY_CRITICAL,
                          app_name='application-3', summary='summary-3',
                          body='body-3', category='cat-3'),
            ]),
        ]

        gtk.gtk_notifier('hub')

        mock_backoff.assert_called_once_with(300, 30, 5)
        mock_NotificationServer.assert_called_once_with('hub', None, True)
        mock_init.assert_called_once_with('app_name')
        mock_Notification.assert_has_calls([
            mock.call('Starting', 'app_name is starting up'),
            mock.call().set_category('network'),
            mock.call().set_urgency(protocol.URGENCY_LOW),
            mock.call().show(),
            mock.call('summary-1', 'body-1'),
            mock.call().set_category('cat-1'),
            mock.call().set_urgency(protocol.URGENCY_LOW),
            mock.call().show(),
            mock.call('summary-2', 'body-2'),
            mock.call().set_category(''),
            mock.call().set_urgency(protocol.URGENCY_NORMAL),
            mock.call().show(),
            mock.call('summary-3', 'body-3'),
            mock.call().set_category('cat-3'),
            mock.call().set_urgency(protocol.URGENCY_CRITICAL),
            mock.call().show(),
        ])

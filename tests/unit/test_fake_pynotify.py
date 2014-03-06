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

from heyu import fake_pynotify
from heyu import protocol


class InitTest(unittest.TestCase):
    def test_init(self):
        self.assertRaises(Exception, fake_pynotify.init, 'app_name')


class NotificationTest(unittest.TestCase):
    def test_init(self):
        noti = fake_pynotify.Notification('summary', 'message')

        self.assertEqual('summary', noti.summary)
        self.assertEqual('message', noti.message)
        self.assertEqual('', noti.category)
        self.assertEqual(protocol.URGENCY_LOW, noti.urgency)

    def test_update(self):
        noti = fake_pynotify.Notification('summary', 'message')

        result = noti.update('new summary', 'new message')

        self.assertEqual(True, result)
        self.assertEqual('new summary', noti.summary)
        self.assertEqual('new message', noti.message)

    def test_set_category(self):
        noti = fake_pynotify.Notification('summary', 'message')

        noti.set_category('category')

        self.assertEqual('category', noti.category)

    def test_set_urgency(self):
        noti = fake_pynotify.Notification('summary', 'message')

        noti.set_urgency(protocol.URGENCY_CRITICAL)

        self.assertEqual(protocol.URGENCY_CRITICAL, noti.urgency)

    def test_show(self):
        noti = fake_pynotify.Notification('summary', 'message')

        result = noti.show()

        self.assertEqual(True, result)

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

from heyu import util


class ParseHubTest(unittest.TestCase):
    def test_space(self):
        self.assertRaises(util.HubException, util.parse_hub, 'bad hostname')

    def test_bracket(self):
        self.assertRaises(util.HubException, util.parse_hub, 'bad[hostname')
        self.assertRaises(util.HubException, util.parse_hub, 'bad]hostname')
        self.assertRaises(util.HubException, util.parse_hub, '[]')

    def test_colon(self):
        self.assertRaises(util.HubException, util.parse_hub, 'bad:hostname')
        self.assertRaises(util.HubException, util.parse_hub, 'bad:')

    def test_bad_ipv6(self):
        self.assertRaises(util.HubException, util.parse_hub, '::1')
        self.assertRaises(util.HubException, util.parse_hub, '[::1')
        self.assertRaises(util.HubException, util.parse_hub, '::1]')

    def test_bare_hostname(self):
        result = util.parse_hub('hostname')

        self.assertEqual(('hostname', util.HEYU_PORT), result)

    def test_hostname_with_port(self):
        result = util.parse_hub('hostname:1234')

        self.assertEqual(('hostname', 1234), result)

    def test_bare_ipv4(self):
        result = util.parse_hub('127.0.0.1')

        self.assertEqual(('127.0.0.1', util.HEYU_PORT), result)

    def test_ipv4_with_port(self):
        result = util.parse_hub('127.0.0.1:1234')

        self.assertEqual(('127.0.0.1', 1234), result)

    def test_bare_ipv6(self):
        result = util.parse_hub('[::1]')

        self.assertEqual(('::1', util.HEYU_PORT), result)

    def test_ipv6_with_port(self):
        result = util.parse_hub('[::1]:1234')

        self.assertEqual(('::1', 1234), result)

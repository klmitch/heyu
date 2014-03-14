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

# Note that this file exists to eliminate a circular import problem
# that prevents cli_tools from loading subcommands that try to import
# the module; this is reported as issue #2 on cli_tools.

import cli_tools

from heyu import util


@cli_tools.argument('--host', '-H',
                    dest='hub',
                    default=util.default_hub(),
                    type=util.parse_hub,
                    help='Specifies the HeyU hub to subscribe to '
                    'notifications from, as "hostname" or "hostname:port".')
@cli_tools.argument('--cert-conf', '-C',
                    default=None,
                    help='Specifies an alternate path to the certificate '
                    'configuration file.')
@cli_tools.argument('--insecure', '-k',
                    dest='secure',
                    default=True,
                    action='store_false',
                    help='Specifies that SSL should not be used to connect '
                    'to the hub.')
@cli_tools.argument('--debug', '-d',
                    default=False,
                    action='store_true',
                    help='Enables debugging.')
@cli_tools.load_subcommands('heyu.notifier')
def notification_server():
    """
    Starts a HeyU notifier.  The specific notifier is specified as a
    subcommand.
    """

    pass  # pragma: no cover

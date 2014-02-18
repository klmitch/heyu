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

import re


# Default port for the HeyU hub
HEYU_PORT = 4859

# Regular expression for parsing a hub specification
HUB_RE = re.compile(r'^(?P<hostname>[^:\s\[\]]+|\[[0-9a-fA-F:]+\])'
                    r'(?::(?P<port>\d+))?$')


class HubException(Exception):
    """
    Exception raised if there's an error parsing the hub
    specification.
    """

    pass


def parse_hub(hub):
    """
    Parse a hub specification.

    :param hub: The hub specification.  Can be either a bare
                "hostname" or a "hostname:port".  If the hostname is
                an IPv6 address, it should be enclosed in brackets,
                i.e. "[::1]:4859".

    :returns: A tuple of the hostname and integer port number.
    """

    # Interpret the hostname
    match = HUB_RE.match(hub)
    if not match:
        raise HubException("Could not understand hub address '%s'" % hub)

    # Extract the hostname
    hostname = match.group('hostname')
    if hostname[0] == '[':
        # Unwrap an IPv6 address
        hostname = hostname[1:-1]

    # Now extract the port
    port = match.group('port')
    if port is None:
        port = HEYU_PORT
    else:
        port = int(port)

    return (hostname, port)

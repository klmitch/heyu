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

import os
import sys

import cli_tools
import tendril

from heyu import protocol
from heyu import util


class SubmitterException(Exception):
    """
    An exception for reporting errors with the submitter.
    """

    pass


class SubmitterApplication(tendril.Application):
    """
    The application for the submitter, a HeyU client.  The submitter
    is used for submitting a notification to the HeyU hub; it sends a
    "notify" message, and expects either an "accepted" message or an
    "error" message in response.
    """

    def __init__(self, parent, app_name, summary, body,
                 urgency=None, category=None, id=None):
        """
        Initialize a submitter application.  This submits the notification
        to the hub.

        :param parent: The parent of the ``SubmitterApplication``.
                       This will be an instance of
                       ``tendril.Tendril``.
        :param app_name: The name of the application the notification
                         is for.
        :param summary: A summary of the notification.
        :param body: The body of the notification.
        :param urgency: The urgency level for the notification.
                        Optional.
        :param category: A category for the notification.  Optional.
        :param id: The ID of a notification to replace.  Optional.
        """

        # Initialize the application
        super(SubmitterApplication, self).__init__(parent)

        # Set up the desired framer
        parent.framers = tendril.COBSFramer(True)

        # Create the notify message
        kwargs = {
            'app_name': app_name,
            'summary': summary,
            'body': body,
        }
        if urgency is not None:
            kwargs['urgency'] = urgency
        if category is not None:
            kwargs['category'] = category
        if id is not None:
            kwargs['id'] = id
        msg = protocol.Message('notify', **kwargs)

        # Send it
        self.send_frame(msg.to_frame())

    def recv_frame(self, frame):
        """
        Called when a frame is received.  Prints out the notification ID.

        :param frame: The received frame.
        """

        # Parse the frame
        try:
            msg = protocol.Message.from_frame(frame)
            if msg.msg_type == 'accepted':
                print(msg.id)
            elif msg.msg_type == 'error':
                print('Failed to submit notification: %s' % msg.reason,
                      file=sys.stderr)
            else:
                print('Unrecognized protocol message "%s"' % msg.msg_type,
                      file=sys.stderr)
        except ValueError as e:
            print('Failed to parse frame: %s' % e, file=sys.stderr)

        # Close the connection
        self.close()


@cli_tools.argument('summary',
                    help='Summary of the notification.')
@cli_tools.argument('body',
                    nargs='?',
                    default='',
                    help='Body of the notification.')
@cli_tools.argument('--urgency', '-u',
                    default=None,
                    help='Specifies the urgency level '
                    '(low, normal, critical).')
@cli_tools.argument('--app-name', '-a',
                    default=None,
                    help='Specifies the application name.')
@cli_tools.argument('--category', '-c',
                    default=None,
                    help='Specifies the notification category.')
@cli_tools.argument('--host', '-H',
                    default=None,
                    help='Specifies the HeyU hub to submit the '
                    'notification to, as "hostname" or "hostname:port".')
@cli_tools.argument('--id', '-I',
                    default=None,
                    help='Specifies the ID of a notification to replace.')
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
def send_notification(hub, app_name, summary, body,
                      urgency=None, category=None, id=None,
                      cert_conf=None, secure=True):
    """
    Sends a notification via the configured HeyU hub.  The hub address
    is read from the "~/.heyu.hub" file, which should contain either
    "hostname" or "hostname:port".  If the file doesn't exist, and
    "--host" is not given, "localhost" will be tried.  Prints out the
    notification ID if the notification is accepted.  Note that
    certificate configuration is specified in "~/.heyu.cert" by
    default.

    :param hub: The address of the hub, as a tuple of hostname and
                port.
    :param app_name: The name of the application the notification is
                     for.
    :param summary: A summary of the notification.
    :param body: The body of the notification.
    :param urgency: The urgency level for the notification.  Optional.
    :param category: A category for the notification.  Optional.
    :param id: The ID of a notification to replace.  Optional.
    :param cert_conf: The path to the certificate configuration file.
                      Optional.
    :param secure: If ``False``, SSL will not be used.  Defaults to
                   ``True``.
    """

    # Look up the manager
    manager = tendril.get_manager('tcp', util.outgoing_endpoint(hub))
    manager.start()

    # Connect to the hub
    app = tendril.TendrilPartial(SubmitterApplication,
                                 app_name, summary, body,
                                 urgency, category, id)
    wrapper = util.cert_wrapper(cert_conf, 'submitter', secure=secure)
    manager.connect(hub, app, wrapper)


@send_notification.processor
def _normalize_args(args):
    """
    Pre-process arguments before calling ``send_notification()``.
    This ensures the arguments are normalized.

    :param args: The values of the command line arguments for
                 normalization.
    """

    # Start off with the hub data
    hub = args.hub
    if hub is None:
        try:
            with open(os.path.expanduser('~/.heyu.hub')) as f:
                hub = f.read().strip()  # pragma: no cover
        except IOError:
            hub = None

    # Do we have a hub?
    if not hub:
        args.hub = ('127.0.0.1', util.HEYU_PORT)
    else:
        args.hub = util.parse_hub(hub)

    # Next, we need the application name
    if not args.app_name:
        args.app_name = os.path.basename(sys.argv[0])

    # Now, decode the urgency
    if args.urgency:
        urgency = protocol.urgency_map.get(args.urgency.lower())
        if urgency is None:
            raise SubmitterException("Unknown urgency level '%s'" %
                                     args.urgency)
        args.urgency = urgency

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
import signal
import sys
import uuid

import cli_tools
import gevent
import gevent.event
import tendril

from heyu import protocol
from heyu import util


# Pre-defined category values
CONNECTED = 'network.connected'
DISCONNECTED = 'network.disconnected'
ERROR = 'network.error'


class NotifierServer(object):
    """
    Notifier server.  Notifiers instantiate this class, then iterate
    over it to retrieve the actual notifications, which they then
    handle.
    """

    def __init__(self, hub, cert_conf=None, secure=True, app_name=None,
                 app_id=None):
        """
        Initialize a ``NotifierServer`` object.

        :param hub: The address of the hub, as a tuple of hostname and
                    port.
        :param cert_conf: The path to the certificate configuration
                          file.  Optional.
        :param secure: If ``False``, SSL will not be used.  Defaults
                       to ``True``.
        :param app_name: The name of the application.  If not
                         specified, the name is derived from
                         ``sys.argv[0]``.
        :param app_id: A UUID for notifications generated internal to
                       the notifier.  If not specified, a random UUID
                       will be generated.
        """

        # Handle the arguments
        self._hub = hub
        self._manager = tendril.get_manager('tcp', util.outgoing_endpoint(hub))
        self._wrapper = util.cert_wrapper(cert_conf, 'notifier', secure=secure)

        # Save the app name and ID
        self._app_name = app_name or os.path.basename(sys.argv[0])
        self._app_id = app_id or str(uuid.uuid4())

        # Track running status and the queue of notifications
        self._hub_app = None
        self._notifications = []
        self._notify_event = gevent.event.Event()

        # Set up behavior on signals
        gevent.signal(signal.SIGINT, self.stop)
        gevent.signal(signal.SIGTERM, self.stop)
        try:  # pragma: no cover
            # Force an immediate shutdown
            gevent.signal(signal.SIGUSR1, self.shutdown)
        except Exception:  # pragma: no cover
            # Ignore errors; SIGUSR1 isn't everywhere
            pass

    def __iter__(self):
        """
        Implementation of the iteration protocol.  Iteration over the
        object yields an endless stream of notifications.

        :returns: The server object.
        """

        # Ensure we're running
        if self._hub_app is None:
            self.start()

        return self

    def next(self):
        """
        Implementation of the iteration protocol.

        :returns: The next notification from the queue, as a
                  ``heyu.protocol.Message`` object.
        """

        # We may have to loop through a few times before a condition
        # is met, but we will eventually exit either by returning a
        # notification message or by raising StopIteration
        while True:
            # If there's a notification on the queue, pop it off and
            # return it
            try:
                msg = self._notifications.pop(0)
            except IndexError:
                # Indicates there are no notifications...
                self._notify_event.clear()
            else:
                # A notification of None indicates that it's time to
                # exit
                if msg is None:
                    sys.exit()

                return msg

            # Are we still running?
            if self._hub_app is None:
                raise StopIteration()

            # OK, wait for a new notification
            self._notify_event.wait()

    def _acceptor(self, tend):
        """
        Called when a connection is established.  Acceptable for use as an
        acceptor.

        :param tend: The ``tendril.Tendril`` object representing the
                     connection.

        :returns: An instance of ``NotifierApplication``.
        """

        # Set up the application
        self._hub_app = NotifierApplication(tend, self, self._app_name,
                                            self._app_id)

        # Return the application
        return self._hub_app

    def start(self):
        """
        Start the server.  This starts up the manager and establishes a
        connection with the HeyU hub.
        """

        # Don't allow redundant start
        if self._hub_app is not None:
            raise ValueError('server is already running')

        # The connection is being initiated but isn't yet complete;
        # we'll use True to differentiate that from the actual
        # application so we can handle the case properly in stop().
        # We set this here since the TCP manager in Tendril doesn't
        # return from connect() until the acceptor has returned.
        self._hub_app = True

        # Start the manager and connect to the hub
        self._manager.start()
        self._manager.connect(self._hub, self._acceptor, self._wrapper)

    def stop(self, *args):
        """
        Stop the server.  This disconnects and shuts down the manager.
        Extra arguments are ignored, so that this method may be used
        as a signal handler.
        """

        # Do nothing if we're not running
        if self._hub_app is None:
            return

        # Stop the manager
        self._manager.stop()

        # Disconnect the client if we can
        if self._hub_app is not True:
            self._hub_app.disconnect()

        self._hub_app = None

        # If arguments were passed, we were called via a signal; add a
        # sentinel to the queue to indicate that we should exit
        if args:
            self._notifications.append(None)

        # Set the flag on the event to ensure next() doesn't block
        self._notify_event.set()

    def shutdown(self, *args):
        """
        Shut the server down.  This is a nasty version of ``stop()``, in
        that the hub connection is simply dropped rather than nicely
        shut down.  Extra arguments are ignored, so that this method
        may be used as a signal handler.
        """

        # Do nothing if we're not running
        if self._hub_app is None:
            return

        # Shut down the manager
        self._manager.shutdown()

        # The client was closed by the shutdown, so clear _hub_app
        self._hub_app = None

        # This also clears the pending notifications
        self._notifications = [None]

        # Set the flag on the event to ensure next() doesn't block
        self._notify_event.set()

    def notify(self, msg):
        """
        Queue up a new notification to be produced by the iterator.

        :param msg: A dictionary describing the notification.
        """

        # Append the notification and set the event
        self._notifications.append(msg)
        self._notify_event.set()


class NotifierApplication(object):
    """
    The application for the notifier, which subscribes to
    notifications from the HeyU server.
    """

    def __init__(self, parent, server, app_name, app_id):
        """
        Initialize a HeyU notifier application.

        :param parent: The parent of the ``NotifierApplication``.
                       This will be an instance of
                       ``tendril.Tendril``.
        :param server: The underlying HeyU notifier server instance.
                       The server provides an iterator interface for
                       the use of notifiers.
        :param app_name: The name of the application, to use in
                         generated notifications, such as the
                         connected notification.
        :param app_id: A UUID for notifications generated internal to
                       the notifier.
        """

        # Initialize the application
        super(NotifierApplication, self).__init__(parent)

        # Save the server link
        self.server = server

        # Save the other data
        self.app_name = app_name
        self.app_id = app_id

        # Set up the desired framer
        parent.framers = tendril.COBSFramer(True)

        # We need to subscribe to receive notifications
        subscribe = protocol.Message('subscribe')
        self.send_frame(subscribe.to_frame())

    def recv_frame(self, frame):
        """
        Called when a frame is received.  Dispatches the appropriate
        method based on the received message.

        :param frame: The received frame.
        """

        # Parse the frame and dispatch to the appropriate handler
        try:
            msg = protocol.Message.from_frame(frame)
            if msg.msg_type == 'notify':
                # Dispatch directly to the server
                self.server.notify(msg)
            elif msg.msg_type == 'subscribed':
                # Generate a notification to let the notifier know
                self.notify('Connection Established', 'The connection to the '
                            'HeyU hub has been established.', CONNECTED)
            elif msg.msg_type == 'goodbye':
                # Disconnect from the server
                self.disconnect()

                # Send the closed notification to the server
                self.closed(None)
            elif msg.msg_type == 'error':
                # Some error occurred
                self.notify('Communication Error', 'An error occurred '
                            'communicating with the HeyU hub: %s' % msg.reason,
                            ERROR)

                # Close the connection
                self.disconnect()

                # We have to manually stop the server; we don't call
                # closed() because we don't want to overwrite the
                # communication error notification
                self.server.stop()
            else:
                # Unknown message type from the server
                self.notify('Unknown Server Message', 'An unrecognized '
                            'server message of type "%s" was received.',
                            ERROR)

                # It should be safe to just ignore the message
        except ValueError as e:
            # Failed to parse the message
            self.notify('Failed To Parse Server Message', 'Unable to parse '
                        'a message from the server: %s' % e, ERROR)

            # Close the connection
            self.disconnect()

            # We have to manually stop the server; we don't call
            # closed() because we don't want to overwrite the
            # communication error notification
            self.server.stop()

    def disconnect(self):
        """
        Disconnect from the server.
        """

        # Send a "goodbye" message
        try:
            self.send_frame(protocol.Message('goodbye').to_frame())
        except Exception:
            pass

        self.close()

    def closed(self, error):
        """
        Called to notify the application that the connection has been
        closed.  Not called if the ``close()`` method is called.  This
        ensures that the server is stopped.
        """

        # Generate an informational notification
        self.notify('Connection Closed', 'The connection to the HeyU hub '
                    'has been closed.', DISCONNECTED)

        # Stop the server
        self.server.stop()

    def notify(self, summary, body, category):
        """
        Directly generates a notification to pass on to the notifier.

        :param summary: The summary for the notification.
        :param body: The body text for the notification.
        :param category: One of the values CONNECTED, DISCONNECTED, or
                         ERROR.  This will be used to set the category
                         of the generated notification.
        """

        msg = protocol.Message('notify', summary=summary, body=body,
                               category=category, app_name=self.app_name,
                               id=self.app_id)
        self.server.notify(msg)


@cli_tools.argument('--host', '-H',
                    dest='hub',
                    action=util.HubAction,
                    default=util.default_hub(),
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
                    help='Enables debugging.')
@cli_tools.load_subcommands('heyu.notifier')
def notification_server():
    """
    Starts a HeyU notifier.  The specific notifier is specified as a
    subcommand.
    """

    pass  # pragma: no cover

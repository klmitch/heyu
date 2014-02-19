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

import socket
import uuid

import cli_tools
import tendril

from heyu import protocol
from heyu import util


class HubServer(object):
    """
    The core persistent data store for the HeyU hub.  This keeps track
    of notification subscribers and forwards the notification messages
    on to them.
    """

    def __init__(self, *endpoints):
        """
        Initialize a ``Server`` object.  Each positional argument is taken
        to be a tuple of address and port to listen on.
        """

        # A dictionary to keep track of the subscribers
        self._subscribers = {}

        # A dictionary to keep track of the listeners
        self._listeners = {}

        # Set up the tendril managers
        if not endpoints:
            endpoints = (('', 0),)
        for endpoint in endpoints:
            self._listeners[endpoint] = tendril.get_manager('tcp', endpoint)

    def _acceptor(self, tend):
        """
        Called when a connection is accepted.  Acceptable for use as an
        acceptor.

        :param tend: The ``tendril.Tendril`` object representing the
                     connection.

        :returns: An instance of ``HubApplication``.
        """

        return HubApplication(tend, self)

    def start(self, cert_conf=None, secure=True):
        """
        Start the server.  This ensures that the hub can receive
        connections on the declared endpoints.

        :param cert_conf: The path to the certificate configuration
                          file.  Optional.
        :param secure: If ``False``, SSL will not be used.  Defaults
                       to ``True``.
        """

        # Get the wrapper
        wrapper = util.cert_wrapper(cert_conf, 'hub', secure=secure)

        # Walk through all managers and start them
        for manager in self._listeners.values():
            manager.start(self._acceptor, wrapper)

    def stop(self):
        """
        Stop the server.  This stops the listening threads and disconnects
        all the clients.
        """

        # Walk through all managers and stop them
        for manager in self._listeners.values():
            manager.stop()

        # Now walk through all the subscribers and disconnect them
        for client, _version in self._subscribers.values():
            client.disconnect()

    def shutdown(self):
        """
        Shut the server down.  This is a nasty version of ``stop()``, in
        that all connections are simply dropped rather than nicely
        shut down.
        """

        # Walk through all managers and shut them down
        for manager in self._listeners.values():
            manager.shutdown()

        # All subscriber connections were closed by shutdown, so clear
        # the the sibscribers list
        self._subscribers = {}

    def subscribe(self, client, version):
        """
        Subscribe a client to notifications.

        :param client: An instance of ``HubApplication`` representing
                       the subscribing client.
        :param version: The protocol version to use when communicating
                        with the client.  Currently, the only
                        recognized version is 0.
        """

        # Add the client to the dictionary of subscribers
        self._subscribers[id(client)] = (client, version)

    def unsubscribe(self, client):
        """
        Unsubscribe a client from notifications.

        :param client: An instance of ``HubApplication`` representing
                       the client to unsubscribe.
        """

        # Remove the client from the dictionary of subscribers
        self._subscribers.pop(id(client), None)

    def submit(self, msg):
        """
        Submit a notification to all current subscribers.

        :param msg: The ``heyu.protocol.Message`` object containing
                    the notification to forward.
        """

        # Forward the message to all subscribers
        for client, version in self._subscribers.values():
            try:
                client.send_frame(msg.to_frame(version))
            except Exception:
                # Ignore failures
                pass


class HubApplication(tendril.Application):
    """
    The application for the hub, the HeyU server.  The hub receives
    notifications from submitters and forwards them to the notifiers.
    Each instance of this class represents a single HeyU client.
    """

    def __init__(self, parent, server):
        """
        Initialize a HeyU client application.

        :param parent: The parent of the ``HubApplication``.  This
                       will be an instance of ``tendril.Tendril``.
        :param server: The underlying HeyU server instance.  The
                       server keeps track of subscriptions and
                       forwards notifications to the subscribers.
        """

        # Initialize the application
        super(HubApplication, self).__init__(parent)

        # Save the server link
        self.server = server

        # Are we a persistent connection?
        self.persist = False

        # Set up the desired framer
        parent.framers = tendril.COBSFramer(True)

        # Determine the hostname of the client
        try:
            if parent.addr[0] in ('127.0.0.1', '::1'):
                self.hostname = socket.getfqdn()
            else:
                self.hostname, _port = socket.getnameinfo(parent.addr, 0)
        except Exception:
            # Just use the bare address
            self.hostname = parent.addr[0]

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
                self.notify(msg)
            elif msg.msg_type == 'subscribe':
                self.subscribe(msg)
            elif msg.msg_type == 'goodbye':
                self.disconnect()
            else:
                # Unknown message type
                reason = 'Unknown message type "%s"' % msg.msg_type
                reply = protocol.Message('error', reason=reason)
                self.send_frame(reply.to_frame())

                # Close the connection
                self.close()
        except ValueError as e:
            reason = 'Failed to decode message: %s' % e
            reply = protocol.Message('error', reason=reason)
            self.send_frame(reply.to_frame())

            # Close the connection
            self.close()

    def notify(self, msg):
        """
        A notification was received; the notification will be forwarded to
        the subscribers.

        :param msg: The ``heyu.protocol.Message`` object describing
                    the message.
        """

        # First, determine the message ID
        id = msg.id or str(uuid.uuid4())

        # Augment the app_name with the origin host name
        app_name = '[%s]%s' % (self.hostname, msg.app_name)

        # Generate a notification message
        notif = protocol.Message('notify', id=id, app_name=app_name,
                                 summary=msg.summary, body=msg.body,
                                 urgency=msg.urgency, category=msg.category)

        # Submit it to the subscribers
        try:
            self.server.submit(notif)
        except Exception as e:
            # Notify of the error
            reason = 'Failed to submit notification: %s' % e
            reply = protocol.Message('error', reason=reason)
        else:
            # It's been accepted; send the appropriate response
            reply = protocol.Message('accepted', id=id)

        # Send the reply and close the connection if necessary
        self.send_frame(reply.to_frame())
        if not self.persist:
            self.close()

    def subscribe(self, msg):
        """
        A subscription request was received; subscribe the client to
        notifications.

        :param msg: The ``heyu.protocol.Message`` object describing
                    the message.
        """

        # Subscribe the client to notifications
        try:
            self.server.subscribe(self, msg.version)
        except Exception as e:
            # Notify of the error
            reason = 'Failed to subscribe: %s' % e
            reply = protocol.Message('error', reason=reason)
        else:
            # It's been accepted; send the appropriate response
            reply = protocol.Message('subscribed')

            # Transform ourself into a persistent client
            self.persist = True

        # Send the reply and close the connection if necessary
        self.send_frame(reply.to_frame())
        if not self.persist:
            self.close()

    def disconnect(self):
        """
        Causes the client to be disconnected from the server.
        """

        # Clean up client subscriptions, if any
        self.server.unsubscribe(self)

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
        ensures that the client is unsubscribed on disconnection.
        """

        # Clean up client subscriptions, if any
        self.server.unsubscribe(self)

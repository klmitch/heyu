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

import cli_tools

try:
    import pynotify
except ImportError:
    from heyu import fake_pynotify as pynotify

from heyu import notifier
from heyu import protocol


@cli_tools.console
def gtk_notification_driver(hub, cert_conf=None, secure=True):
    """
    GTK notification driver.  This uses the PyGTK package "pynotify"
    to generate desktop notifications from the notifications received
    from the HeyU hub.

    :param hub: The address of the hub, as a tuple of hostname and
                port.
    :param cert_conf: The path to the certificate configuration file.
                      Optional.
    :param secure: If ``False``, SSL will not be used.  Defaults to
                   ``True``.
    """

    # Set up the server
    server = notifier.NotifierServer(hub, cert_conf, secure)

    # Initialize pynotify
    pynotify.init(server.app_name)

    # Need a dictionary mapping notification IDs to
    # pynotify.Notification instances
    notifications = {}

    # Set up our direct notification
    notifications[server.app_id] = pynotify.Notification(
        "Starting", "%s is starting up" % server.app_name)
    notifications[server.app_id].set_category('network')
    notifications[server.app_id].set_urgency(protocol.URGENCY_LOW)
    notifications[server.app_id].show()

    # Keep connected to the HeyU hub
    while True:
        # Consume notifications
        for msg in server:
            # Get a Notification instance
            noti = notifications.get(msg.id)
            if noti is None:
                noti = pynotify.Notification(msg.summary, msg.body)
                notifications[msg.id] = noti
            else:
                noti.update(msg.summary, msg.body)

            # Update category and urgency
            noti.set_category(msg.category or '')
            noti.set_urgency(msg.urgency)

            # Show the notification
            noti.show()

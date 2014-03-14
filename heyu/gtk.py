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

import time

import cli_tools

try:
    import pynotify
except ImportError:
    from heyu import fake_pynotify as pynotify

from heyu import notifications
from heyu import protocol


def backoff(max_sleep, threshold, recover):
    """
    A generator that performs exponential backoff by sleeping each
    time through with a constantly updated sleep time.  When the
    operation is successful (elapsed time greater than the
    ``threshold``), the sleep time is scaled back linearly by the
    ``recover`` factor; when unsuccessful, the sleep time is increased
    exponentially until the maximum sleep time is reached.

    :param max_sleep: The maximum number of seconds that ``backoff()``
                      will sleep for.
    :param threshold: The minimum number of seconds required for the
                      operation to be considered successful.  Before
                      ``threshold``, sleep time is increased
                      exponentially; after ``threshold``, sleep time
                      is decreased linearly.
    :param recover: A scaling factor used for linear decrease in the
                    sleep time.  The elapsed time is divided by this
                    factor, truncated to integer, and subtracted from
                    the last sleep time, when the operation is
                    successful.
    """

    # Initialize the factors from the previous iteration of the loop
    last_time = time.time()
    last_sleep = 0

    # An infinite generator
    while True:
        # Perform the operation.  Success or failure is judged based
        # on the amount of time before execution continues in this
        # context, under control of the threshold parameter.
        yield

        # Calculate the elapsed time
        curr_time = time.time()
        elapsed = curr_time - last_time

        # Was the operation successful?
        if elapsed < threshold:
            # No, double the last_sleep time, capping at max_sleep
            next_sleep = min(max(last_sleep * 2, 1), max_sleep)
        else:
            # Yes, linearly scale the last_sleep time with a minimum
            # of 0
            next_sleep = max(last_sleep - int(elapsed / recover), 0)

        # Sleep...
        time.sleep(next_sleep)

        # Prepare for the next trip around the loop
        last_time = curr_time
        last_sleep = next_sleep


@cli_tools.argument('--max-backoff', '-B',
                    default=300,
                    type=int,
                    help='The maximum amount of backoff, in seconds.  After '
                    'a connection failure, this is the maximum amount of time '
                    'to sleep prior to the next attempt to connect.')
@cli_tools.argument('--threshold', '-T',
                    default=30,
                    type=int,
                    help='The minimum number of seconds before the connection '
                    'is considered a success.  If the connection fails prior '
                    'to this, the time before the next attempt is doubled.  '
                    'If the connection fails after this, the time before the '
                    'next attempt is reduced linearly.')
@cli_tools.argument('--recover', '-R',
                    default=5,
                    type=int,
                    help='The scaling factor for the linear reduction of the '
                    'time to the next connection attempt.  The number of '
                    'seconds since the last attempt is divided by this '
                    'factor and used to reduce the time before the next '
                    'connection attempt.')
def gtk_notifier(hub, cert_conf=None, secure=True,
                 max_sleep=300, threshold=30, recover=5):
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
    :param max_sleep: The maximum number of seconds that ``backoff()``
                      will sleep for.
    :param threshold: The minimum number of seconds required for the
                      operation to be considered successful.  Before
                      ``threshold``, sleep time is increased
                      exponentially; after ``threshold``, sleep time
                      is decreased linearly.
    :param recover: A scaling factor used for linear decrease in the
                    sleep time.  The elapsed time is divided by this
                    factor, truncated to integer, and subtracted from
                    the last sleep time, when the operation is
                    successful.
    """

    # Set up the server
    server = notifications.NotificationServer(hub, cert_conf, secure)

    # Initialize pynotify
    pynotify.init(server.app_name)

    # Need a dictionary mapping notification IDs to
    # pynotify.Notification instances
    notifies = {}

    # Set up our direct notification
    notifies[server.app_id] = pynotify.Notification(
        "Starting", "%s is starting up" % server.app_name)
    notifies[server.app_id].set_category('network')
    notifies[server.app_id].set_urgency(protocol.URGENCY_LOW)
    notifies[server.app_id].show()

    # Keep connected to the HeyU hub
    for _dummy in backoff(max_sleep, threshold, recover):
        # Consume notifications
        for msg in server:
            # Get a Notification instance
            noti = notifies.get(msg.id)
            if noti is None:
                noti = pynotify.Notification(msg.summary, msg.body)
                notifies[msg.id] = noti
            else:
                noti.update(msg.summary, msg.body)

            # Update category and urgency
            noti.set_category(msg.category or '')
            noti.set_urgency(msg.urgency)

            # Show the notification
            noti.show()

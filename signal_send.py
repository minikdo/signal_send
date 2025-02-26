#!/usr/bin/env python3

import os
import sys
import json
from datetime import datetime as dt
import uuid
from re import findall as re_findall
import argparse
import signal
import requests

from .settings import URL
from .emoicons import emoicons


TIMEOUT = 120
MSG_CHAR_LIMIT = 5000


class AlarmException(Exception):
    pass


def alarm_handler(signum, frame):
    raise AlarmException


parser = argparse.ArgumentParser()
parser.add_argument("recipient", nargs=1)
parser.add_argument("message", nargs="?")
parser.add_argument("-l", "--list", action="store_true", help="list contacts")
parser.add_argument("-r", "--remove", action="store_true",
                    help="remove contact")
parser.add_argument("-e", "--emoicons", action="store_true",
                    help="list emoicons")

args = parser.parse_args()


with open(
        f"{os.path.expanduser('~')}/.local/share/signal-send/contacts.json",
        "r") as f:
    contacts = iter(json.load(f))


def istartswith(name, pattern):
    if name is None:
        return None
    return name.lower().startswith(pattern)


def find_contact(pattern):

    results = []
    while result := next(
            (i
             for i in contacts
             if istartswith(i["profile"]["givenName"], pattern)), False):
        results.append(result)
    return results


def replace_emoicons(message):

    abbrevs = re_findall(r"::(\w+)", message)

    for a in set(abbrevs):
        try:
            emoicon = emoicons[a]
        except KeyError:
            print("Emoicon not found.")
            sys.exit(1)

        message = message.replace(f"::{a}", emoicon)
    return message


def send_message(message, recipient):

    if "::" in message:
        message = replace_emoicons(message)

    payload = {
        "id": str(uuid.uuid1()),
        "jsonrpc": "2.0",
        "method": "send",
        "params": {
            "message": message,
            "recipient": recipient
        }
    }

    response = requests.post(URL, json=payload, timeout=10)
    response = response.json()

    timestamp = response['result']['timestamp'] / 1000.0
    timestamp_orig = response['result']['timestamp']
    timestamp = dt.fromtimestamp(timestamp).strftime('%H:%M:%S')

    result = []
    for item in response['result']['results']:
        number = item['recipientAddress']['number']
        status = item['type']
        result.append((number, status))

    return timestamp, result, timestamp_orig


def remote_delete(recipient, timestamp):

    payload = {
        "id": str(uuid.uuid1()),
        "jsonrpc": "2.0",
        "method": "remoteDelete",
        "params": {
            "target-timestamp": timestamp,
            "recipient": recipient
        }
    }

    response = requests.post(URL, json=payload, timeout=10)
    response = response.json()

    return response


def remove_contact(recipient):

    payload = {
        "id": str(uuid.uuid1()),
        "jsonrpc": "2.0",
        "method": "removeContact",
        "params": {
            "identifier": recipient,
        }
    }

    response = requests.post(URL, json=payload, timeout=10)
    response = response.json()

    return response


def main():

    if args.list:
        from tabulate import tabulate
        res = []
        for contact in contacts:
            name = f"{contact['profile']['givenName'] or '?'} "
            name += f"{contact['profile']['familyName'] or ''}"
            res.append([
                name.lower(),
                contact['number'],
                contact['uuid'],
            ])
        res.sort(key=lambda e: (e[0] is None, e[0]))
        print(tabulate(res,
                       headers=('Name', 'Number', 'UUID'),
                       showindex=True))
        sys.exit(0)

    if args.remove:
        result = remove_contact(args.recipient)
        print(result)

        sys.exit(0)

    if args.emoicons:
        print(emoicons)
        sys.exit(0)

    recipient = find_contact(args.recipient[0])

    if len(recipient) == 0:
        print('no recipient found.')
        sys.exit(1)

    if len(recipient) > 1:
        print('more than 1 found!')
        results = [r['profile']['givenName'] for r in recipient]
        print(results)
        sys.exit(1)

    recipient = recipient[0]
    recipient_number = recipient.get("number")
    recipient_uuid = recipient.get("uuid")
    recipient_givenname = recipient["profile"]["givenName"]
    recipient_familyname = recipient["profile"]["familyName"]

    if 'profile' in recipient:
        recipient_name = f"{recipient_givenname} {recipient_familyname or ''}"

    message = args.message

    # Check pipe
    if message == '-' and not os.isatty(sys.stdin.fileno()):
        message = sys.stdin.read()
        if len(message) > MSG_CHAR_LIMIT:
            print(f"Input exceedes {MSG_CHAR_LIMIT} characters. Exiting...")
            sys.exit(1)

    if message is None:
        print("Run interactive mode for "
              f"{recipient_name}{recipient_number or recipient_uuid}")

        timestamp_orig = 0
        while True:
            signal.signal(signal.SIGALRM, alarm_handler)
            signal.alarm(TIMEOUT)

            try:
                message = input(f"({recipient_givenname})> ")
                signal.alarm(0)
            except AlarmException:
                print(f'\nInput timeout {TIMEOUT} sec. Quitting...')
                sys.exit(0)

            n = len(recipient_givenname) + 2 + len(message) + 3

            # Quit interactive mode
            if message == 'q':
                print("quit.")
                sys.exit(0)

            if message == 'del':
                result = remote_delete(recipient_uuid, timestamp_orig)
                print(result['result']['results'])
                break

            # Protect sending to someone else
            if message.startswith("s "):
                print("s ??? quitting...")
                sys.exit(1)

            timestamp, result, timestamp_orig = send_message(message,
                                                             recipient_uuid)
            if result[0][1] == 'SUCCESS':
                print(f"\033[F\33[{n}C\033[0;34;8m  "
                      f"{timestamp} \033[38;5;239m{timestamp_orig}\033[0;0m")
            else:
                print(f"{timestamp} {result}")

    timestamp, result, _ = send_message(message, recipient_number)
    print(f"{timestamp} {result}")


if __name__ == '__main__':
    main()

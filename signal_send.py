#!/usr/bin/env python3

import os
import sys
from re import findall as re_findall
import requests
import json
import uuid
import argparse
from datetime import datetime as dt
import signal

from .settings import URL
from .emoicons import emoicons
from .recipients import recipients


TIMEOUT = 120

class AlarmException(Exception):
    pass


def alarm_handler(signum, frame):
    raise AlarmException


parser = argparse.ArgumentParser()
parser.add_argument("recipient", nargs="?")
parser.add_argument("message", nargs="?")
parser.add_argument("-l", "--list", action="store_true", help="list contacts")
parser.add_argument("-e", "--emoicons", action="store_true",
                    help="list emoicons")

args = parser.parse_args()


with open(f"{os.path.expanduser('~')}/.local/share/signal-send/contacts.json", "r") as f:
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
    timestamp = dt.fromtimestamp(timestamp).strftime('%H:%M:%S')

    result = []
    for item in response['result']['results']:
        number = item['recipientAddress']['number']
        status = item['type']
        result.append((number, status))

    return timestamp, result


def main():

    if args.list:
        print(json.dumps(recipients, indent=2))
        sys.exit(0)

    if args.emoicons:
        print(emoicons)
        sys.exit(0)

    # try:
    #     recipient = recipients[args.recipient]
    # except KeyError:
    #     print("recipient not found.")
    #     sys.exit(1)

    recipient = find_contact(args.recipient)

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

    if 'profile' in recipient:
        recipient_name = "{} {}".format(
            recipient["profile"]["givenName"],
            recipient["profile"]["familyName"]
        )

    message = args.message

    if message is None:
        print(f"Run interactive mode for {recipient_name} {recipient_number}")

        while True:
            signal.signal(signal.SIGALRM, alarm_handler)
            signal.alarm(TIMEOUT)            
            try:
                message = input("> ")
                signal.alarm(0)
            except AlarmException:
                print(f'\nInput timeout {TIMEOUT} sec. Quitting...')
                sys.exit(0)

            n = len(message) + 3

            # Quit interactive mode
            if message == 'q':
                print("quit.")
                sys.exit(0)

            # Protect sending to someone else
            if message.startswith("s "):
                print("s ??? quitting...")
                sys.exit(1)
                
            timestamp, result = send_message(message, recipient_number)
            if result[0][1] == 'SUCCESS':
                print(f"\033[F\33[{n}C\033[0;34;8m  {timestamp}\033[0;0m")
            else:
                print(f"{timestamp} {result}")
                
    timestamp, result = send_message(message, recipient_number)
    print(f"{timestamp} {result}")


if __name__ == '__main__':
    main()

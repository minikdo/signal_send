#!/usr/bin/env python3

import sys
from re import findall as re_findall
import requests
import json
import uuid
import argparse
from datetime import datetime as dt

from .settings import URL
from .emoicons import emoicons
from .recipients import recipients


parser = argparse.ArgumentParser()
parser.add_argument("recipient", nargs="?")
parser.add_argument("message", nargs="?")
parser.add_argument("-l", "--list", action="store_true", help="list contacts")
parser.add_argument("-e", "--emoicons", action="store_true",
                    help="list emoicons")

args = parser.parse_args()


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

    try:
        recipient = recipients[args.recipient]
    except KeyError:
        print("recipient not found.")
        sys.exit(1)

    message = args.message

    if message is None:
        print("Run interactive mode.")
        while True:
            message = input("> ")
            n = len(message) + 3
            if message == 'q':
                print("quit.")
                sys.exit(0)

            timestamp, result = send_message(message, recipient)
            if result[0][1] == 'SUCCESS':
                print(f"\033[F\33[{n}C\033[0;34;0m {timestamp}\033[0;0m")
            else:
                print(f"{timestamp} {result}")
                
    timestamp, result = send_message(message, recipient)
    print(f"{timestamp} {result}")


if __name__ == '__main__':
    main()

#!/usr/bin/env python3

import sys
import json
import pprint
import time
import requests
import argparse
from datetime import datetime as dt
import sseclient


parser = argparse.ArgumentParser()
parser.add_argument("-d", "--debug", action="store_true", help="debug mode")

args = parser.parse_args()


url = 'http://10.4.2.1:33417/api/v1/events'
headers = {'Accept': 'text/event-stream'}
response = requests.get(url, stream=True, headers=headers)
client = sseclient.SSEClient(response)

def delay_print(text):
    for char in text:
        print(char, end='', flush=True)
        time.sleep(0.07)

def print_inline(text):
    print(text, end='')


CONTACT_COLORS = {
    "edyta121971": "068",
    "marzena szmek": "033",
    "Joanna": "111",
    "jurek1234": "140",
    "Agnieszka Ściwiarska": "222",
}


def main():

    last_date = None

    print("Waiting for data...")
    
    for event in client.events():

        data = json.loads(event.data)

        envelope = data['envelope']

        if 'dataMessage' in envelope:

            data_message = envelope.get('dataMessage')
            source_name = envelope.get('sourceName')

            timestamp = data_message['timestamp'] / 1000.0
            timestamp_obj = dt.fromtimestamp(timestamp)
            strtimestamp = timestamp_obj.strftime('%H:%M:%S')

            # Print a bar on date change
            if last_date != timestamp_obj.date():
                print('=== {} ==='.format(timestamp_obj.strftime('%Y-%m-%d')))

            # Update last_date value
            last_date = timestamp_obj.date()
            
            # Iterate attachments
            attachments = []
            if 'attachments' in data_message:
                attachments.append(
                    [a['contentType'] for a in data_message['attachments']]
                )

            # Change color per user, defaults to gray
            color = CONTACT_COLORS.get(source_name, "249")
            print(f'\033[38;5;{color}m', end='')

            print(f"{strtimestamp} {source_name}:", end=' ')

            msg = data_message.get('message', None)

            print_cmd = print_inline
            # Print with typing imitation on short messages
            if msg is not None and len(msg) < 35:
                print_cmd = delay_print

            if 'reaction' in data_message:
                emoji = data_message['reaction'].get('emoji')
                msg = f'reaction: {emoji}'

            print_cmd(f"{msg} {attachments or ''}")

            # Reset color
            print('\033[39m')

            if args.debug:
                pprint.pprint(data)


if __name__ == '__main__':
    try:
        main()

    except KeyboardInterrupt:
        print('interrupted')
        sys.exit(1)

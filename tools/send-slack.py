#!/usr/bin/env python3

__doc__ = """
This script sends a message to a Slack channel using a webhook URL. It is
intended to be used by CI scripts to send notifications to Slack.
"""

import argparse
import json
import sys

# third_party
import requests


def main():
  """Parses arguments and sends a message to Slack."""

  parser = argparse.ArgumentParser(description="Send message to Slack")
  parser.add_argument(
      "--message", required=True, help="The message to send to Slack")
  parser.add_argument(
      "--input", help="Path to a file to append to the message body")
  parser.add_argument("--url", required=True, help="The Slack webhook URL")
  args = parser.parse_args()

  # Construct the message body
  message = {"text": args.message}

  # Add content from input file if provided
  if args.input:
    try:
      with open(args.input, 'r') as f:
        file_content = f.read()
        message["text"] += "\n```" + file_content + "```"
    except FileNotFoundError:
      print(f"Error: Could not read file {args.input}")
      message["text"] += "\nError: Could not read file"

  # Send the message to Slack
  send_slack_message(args.url, message)


def send_slack_message(url, message):
  """Sends a message to Slack using the provided webhook URL and message body."""

  headers = {"Content-Type": "application/json"}
  data = json.dumps(message).encode("utf-8")

  response = requests.post(url, headers=headers, data=data)
  response.raise_for_status()


if __name__ == "__main__":
  sys.exit(main())

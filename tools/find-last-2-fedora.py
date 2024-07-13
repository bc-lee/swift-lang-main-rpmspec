#!/usr/bin/env python3

__doc__ = """
This script finds the latest Fedora release and the next Fedora release.
If the latest release is branched, the next release is the next branched release,
otherwise it is rawhide.
"""

import os
import sys

# third_party
import requests


def find_latest_release():
  url = "https://endoflife.date/api/fedora.json"
  r = requests.get(url, headers={"Accept": "application/json"})
  r.raise_for_status()

  return int(r.json()[0]["latest"])


def find_next_release(current):
  url = "https://mirrors.fedoraproject.org/mirrorlist?repo=nonexistent&arch=x86_64"
  r = requests.get(url)

  lines = r.text.split("\n")
  current_release = f"fedora-{current}"
  found_current = False
  for line in lines:
    if current_release in line:
      found_current = True
      break
  if not found_current:
    raise ValueError(f"Could not find current release {current} in mirrorlist.")

  next_release = f"fedora-{current + 1}"
  for line in lines:
    if next_release in line:
      # Next release is branched, use it
      return current + 1

  # Not branched yet, use rawhide
  return "rawhide"


def main():
  latest_version = find_latest_release()
  next_version = find_next_release(latest_version)
  print(f"{latest_version} {next_version}")


if __name__ == "__main__":
  sys.exit(main())

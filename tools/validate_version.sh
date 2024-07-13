#!/bin/bash

set -exu

# 1st arg: version.inc
# 2nd arg: base version

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 version.inc <base_version>"
    exit 1
fi

version_inc=$1
base_version=$2
base_version_major=$(echo $base_version | awk -F. '{print $1}')
base_version_minor=$(echo $base_version | awk -F. '{print $2}')

swift_version=$(cat $version_inc | grep 'swift_version' | awk '{print $3}')

echo "swift_version: $swift_version"
echo "base_version: $base_version"

# Check if swift_version is lower than base_version
set +e
rpmdev-vercmp $swift_version $base_version
ret=$?
set -e
# 12 implies first version is lower than second version
if [[ $ret -ne 12 ]]; then
    echo "swift_version is not lower than base_version"
    exit 1
fi

if [[ $base_version_minor -eq 0 ]]; then
  prev_base_version_major=$((base_version_major - 1))
  prev_base_version_minor=99
else
  prev_base_version_major=$base_version_major
  prev_base_version_minor=$((base_version_minor - 1))
fi
prev_base_version="${prev_base_version_major}.${prev_base_version_minor}"

# Check if swift_version is greater than prev_base_version
set +e
rpmdev-vercmp $swift_version $prev_base_version
ret=$?
set -e
# 11 implies first version is greater than second version
if [[ $ret -ne 11 ]]; then
    echo "swift_version is not greater than prev_base_version"
    exit 1
fi

echo "Validation successful"

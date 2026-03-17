#!/bin/bash

set -e

REGION="us-ord"
LINODE_TYPE="g6-dedicated-4"
IMAGE="linode/ubuntu24.04"
UUID=$(uuidgen | awk -F - '{print $1}')

echo "REGION=${REGION}" >> "$GITHUB_ENV"
echo "LINODE_TYPE=${LINODE_TYPE}" >> "$GITHUB_ENV"
echo "IMAGE=${IMAGE}" >> "$GITHUB_ENV"
echo "UUID=${UUID}" >> "$GITHUB_ENV"
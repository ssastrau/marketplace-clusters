#!/bin/bash

set -e

REGION="us-mia"
LINODE_TYPE="g7-dedicated-8-4"
IMAGE="linode/ubuntu24.04"
UUID=$(uuidgen | awk -F - '{print $1}')

echo "REGION=${REGION}" >> "$GITHUB_ENV"
echo "LINODE_TYPE=${LINODE_TYPE}" >> "$GITHUB_ENV"
echo "IMAGE=${IMAGE}" >> "$GITHUB_ENV"
echo "UUID=${UUID}" >> "$GITHUB_ENV"
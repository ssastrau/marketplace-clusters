#!/bin/bash
# CI infrastructure config for <app>. Exports the Linode spec to $GITHUB_ENV.
# Reference: deployment_scripts/linode-marketplace-hashicorp-nomad/linode-config.sh

set -euo pipefail

REGION="us-ord"
LINODE_TYPE="g6-dedicated-4"
IMAGE="linode/ubuntu24.04"

echo "REGION=${REGION}" >> "$GITHUB_ENV"
echo "LINODE_TYPE=${LINODE_TYPE}" >> "$GITHUB_ENV"
echo "IMAGE=${IMAGE}" >> "$GITHUB_ENV"

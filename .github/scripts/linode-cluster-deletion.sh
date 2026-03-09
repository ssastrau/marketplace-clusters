#!/usr/bin/env bash

set -e

if [ -z "$UUID" ] || [ ${#UUID} -lt 4 ]; then
  echo "Error: UUID is empty. Aborting."
  exit 1
fi

LINODES=$(curl -s -H "Authorization: Bearer $LINODE_API_SECRET" \
  https://api.linode.com/v4/linode/instances | \
  jq -r ".data[] | select(.label | contains(\"$UUID\")) | .id")

if [ -n "$LINODES" ]; then
  echo "Found Linodes with UUID $UUID: $LINODES"
  for LINODE_ID in $LINODES; do
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
      -H "Authorization: Bearer $LINODE_API_SECRET" \
      https://api.linode.com/v4/linode/instances/$LINODE_ID)

    if [ "$RESPONSE" = "200" ]; then
      echo "Linode $LINODE_ID deleted successfully."
    else
      echo "Failed to delete Linode $LINODE_ID. Status code: $RESPONSE"
      exit 1
    fi
  done
else
  echo "No Linodes found with UUID: $UUID"
fi

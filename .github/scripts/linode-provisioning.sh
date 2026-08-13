#!/usr/bin/env bash

set -e

TIMEOUT=300
API_URL="https://api.linode.com/v4/linode/instances"
RESPONSE_FILE=$(mktemp)

PAYLOAD=$(jq -n \
	--arg image "$IMAGE" \
	--arg region "$REGION" \
	--arg type "$LINODE_TYPE" \
	--arg label "github-${APP_NAME}" \
	--arg root_pass "$LINODE_ROOT_PASS" \
	--arg ssh_key "$LINODE_PUBLIC_SSH_KEY" \
	'{
		image: $image,
		region: $region,
		type: $type,
		label: $label,
		root_pass: $root_pass,
		authorized_keys: [$ssh_key],
		private_ip: false,
		maintenance_policy: "linode/migrate",
		disk_encryption: "enabled"
	}')

HTTP_CODE=$(curl -s -o "$RESPONSE_FILE" -w "%{http_code}" \
	--retry 3 --retry-delay 5 \
	-H "Content-Type: application/json" \
	-H "Authorization: Bearer $LINODE_API_SECRET" \
	-X POST -d "$PAYLOAD" "$API_URL")

if [ "$HTTP_CODE" != "200" ]; then
	echo "Linode creation failed with status code $HTTP_CODE"
	cat "$RESPONSE_FILE"
	exit 1
fi

LINODE_ID=$(jq -r '.id' "$RESPONSE_FILE")
echo "LINODE_ID=$LINODE_ID" >>"$GITHUB_OUTPUT"

LINODE_IPV4=$(jq -r '.ipv4[0]' "$RESPONSE_FILE")
echo "::add-mask::$LINODE_IPV4"
echo "LINODE_IPV4=$LINODE_IPV4" >>"$GITHUB_OUTPUT"

DEADLINE=$((SECONDS + TIMEOUT))

while true; do
	STATUS=$(curl -s -H "Authorization: Bearer $LINODE_API_SECRET" "$API_URL/$LINODE_ID" | jq -r '.status')
	echo "Current Linode status: $STATUS"

	if [ "$STATUS" = "running" ]; then
		break
	fi

	if [ "$SECONDS" -ge "$DEADLINE" ]; then
		echo "Timeout reached. Linode provisioning failed."
		exit 1
	fi

	sleep 10
done

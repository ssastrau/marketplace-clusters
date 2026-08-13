#!/usr/bin/env bash

set -e

SSH_TIMEOUT=600
DEPLOYMENT_SCRIPT="${APP_NAME#linode-marketplace-}-deploy.sh"
REMOTE_DIR="/root/deployment"
SSH_KEY="$HOME/.ssh/id_linode"

mkdir -p ~/.ssh
echo "$LINODE_PRIVATE_SSH_KEY" > "$SSH_KEY"
chmod 600 "$SSH_KEY"

SSH_OPTS=(
  -i "$SSH_KEY"
  -o StrictHostKeyChecking=no
  -o PasswordAuthentication=no
  -o BatchMode=yes
  -o ConnectTimeout=10
  -o ServerAliveInterval=30
  -o ServerAliveCountMax=10
  -o TCPKeepAlive=yes
)

wait_for_ssh() {
  local deadline=$((SECONDS + SSH_TIMEOUT))

  until ssh "${SSH_OPTS[@]}" "root@$LINODE_IPV4" "exit"; do
    if [ "$SECONDS" -ge "$deadline" ]; then
      echo "Timeout reached after ${SSH_TIMEOUT}s. Unable to connect to Linode via SSH."
      exit 1
    fi
    echo "Waiting for SSH to be ready... ($((deadline - SECONDS))s remaining)"
    sleep 10
  done

  echo "Connected to Linode via SSH"
}

copy_deployment_scripts() {
  echo "Copying deployment_scripts/$APP_NAME to $REMOTE_DIR"
  scp -r "${SSH_OPTS[@]}" \
  "deployment_scripts/$APP_NAME" \
  "root@$LINODE_IPV4:$REMOTE_DIR"
}

run_remote_deploy() {
  echo "Deploying $APP_NAME on $IMAGE image"

  set +e
  ssh "${SSH_OPTS[@]}" \
  "root@$LINODE_IPV4" \
  "
   export LINODE_API_SECRET=$LINODE_API_SECRET
   export LINODE_ID=$LINODE_ID
   export GH_USER=$GH_USER
   export BRANCH=$BRANCH
   export APP_NAME=$APP_NAME
   export DEPLOYMENT_SCRIPT=$DEPLOYMENT_SCRIPT
   export UUID=$UUID

   cd $REMOTE_DIR
   chmod +x test-vars.sh $DEPLOYMENT_SCRIPT
   . ./test-vars.sh
   ./$DEPLOYMENT_SCRIPT
   "

  local rc=$?
  set -e

  if [ "$rc" -eq 255 ]; then
    echo "SSH disconnected (exit 255). Assuming remote reboot occurred; continuing."
    rc=0
  fi

  if [ "$rc" -ne 0 ]; then
    echo "Remote deployment failed with exit code $rc"
    exit "$rc"
  fi
}

wait_for_ssh
copy_deployment_scripts
run_remote_deploy
wait_for_ssh

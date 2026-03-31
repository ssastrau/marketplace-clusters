#!/bin/bash
set -e
trap "cleanup $? $LINENO" EXIT

## Deployment Variables
# <UDF name="token_password" label="Your Linode API token" />
# <UDF name="cluster_name" label="Domain Name" />
# <UDF name="sudo_username" label="The limited sudo user to be created in the cluster" />
# <UDF name="add_ssh_keys" label="Add Account SSH Keys to All Nodes?" oneof="yes,no"  default="yes" />
# <UDF name="cluster_size" label="PostgeSQL cluster size" default="3" oneof="3" />

# set force apt non-interactive
export DEBIAN_FRONTEND=noninteractive

# git repo
export GIT_REPO="https://github.com/akamai-compute-marketplace/postgresql-occ.git"

# enable logging
exec > >(tee /dev/ttyS0 /var/log/stackscript.log) 2>&1
# source script libraries
source <ssinclude StackScriptID=1>
function cleanup {
  if [ "$?" != "0" ] || [ "$SUCCESS" == "true" ]; then
    #deactivate
    cd ${HOME}
    if [ -d "/tmp/postgresql-cluster" ]; then
      rm -rf /tmp/postgresql-cluster
    fi
    if [ -d "/usr/local/bin/run" ]; then
      rm /usr/local/bin/run
    fi
    stackscript_cleanup
  fi
}
function add_privateip {
  echo "[info] Adding instance private IP"
  curl -H "Content-Type: application/json" \
      -H "Authorization: Bearer ${TOKEN_PASSWORD}" \
      -X POST -d '{
        "type": "ipv4",
        "public": false
      }' \
      https://api.linode.com/v4/linode/instances/${LINODE_ID}/ips
}
function get_privateip {
  curl -s -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${TOKEN_PASSWORD}" \
   https://api.linode.com/v4/linode/instances/${LINODE_ID}/ips | \
   jq -r '.ipv4.private[].address'
}
function configure_privateip {
  LINODE_IP=$(get_privateip)
  if [ ! -z "${LINODE_IP}" ]; then
          echo "[info] Linode private IP present"
  else
          echo "[info] No private IP found. Adding.."
          add_privateip
          LINODE_IP=$(get_privateip)
          ip addr add ${LINODE_IP}/17 dev eth0 label eth0:1
  fi
}
function rename_provisioner {
  INSTANCE_PREFIX=$(curl -sH "Authorization: Bearer ${TOKEN_PASSWORD}" "https://api.linode.com/v4/linode/instances/${LINODE_ID}" | jq -r .label)
  export INSTANCE_PREFIX="${INSTANCE_PREFIX}"
  echo "[+] renaming the provisioner"
  curl -s -H "Content-Type: application/json" \
      -H "Authorization: Bearer ${TOKEN_PASSWORD}" \
      -X PUT -d "{
        \"label\": \"${INSTANCE_PREFIX}1\"
      }" \
      https://api.linode.com/v4/linode/instances/${LINODE_ID}
}
function setup {
  # install dependancies
  export DEBIAN_FRONTEND=non-interactive
  apt-get update && apt-get upgrade -y
  apt-get install -y jq git python3 python3-pip python3-dev build-essential firewalld
  # add private IP address
  rename_provisioner
  configure_privateip
  # write authorized_keys file
  if [ "${ADD_SSH_KEYS}" == "yes" ]; then
    if [ ! -d ~/.ssh ]; then 
            mkdir ~/.ssh
    else 
            echo ".ssh directory is already created"
    fi
    curl -sH "Content-Type: application/json" -H "Authorization: Bearer ${TOKEN_PASSWORD}" https://api.linode.com/v4/profile/sshkeys | jq -r .data[].ssh_key > /root/.ssh/authorized_keys
  fi
  # clone repo and set up ansible environment
  git clone ${GIT_REPO} /tmp/postgresql-cluster
  cd /tmp/postgresql-cluster
  pip3 install virtualenv
  python3 -m virtualenv env
  source env/bin/activate
  pip install pip --upgrade
  pip install -r requirements.txt
  ansible-galaxy install -r collections.yml
  # copy run script to path
  cp scripts/run.sh /usr/local/bin/run
  chmod +x /usr/local/bin/run
}
# main
setup
run ansible:build
run ansible:deploy && export SUCCESS="true"

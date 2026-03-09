#!/bin/bash
set -e
DEBUG="NO"
if [ "${DEBUG}" == "NO" ]; then
  trap "cleanup $? $LINENO" EXIT
fi

## Deployment Variables
# <UDF name="token_password" label="Your Linode API token" />
# <UDF name="cluster_name" label="Cluster Name" />
# <UDF name="sudo_username" label="The limited sudo user to be created in the cluster" />
# <UDF name="cluster_size" label="Apache Spark cluster size" default="3" oneof="3,4,5,6,7,8,9,10" />
# <UDF name="soa_email_address" label="Email address for Let's Encrypt Certificates" />
# <UDF name="spark_user" label="User to login to Spark WebUI" />
# <UDF name="add_ssh_keys" label="Add Account SSH Keys to All Nodes?" oneof="yes,no"  default="yes" />

## Domain Settings
#<UDF name="subdomain" label="Subdomain" example="The subdomain for the DNS record. `www` will be entered if no subdomain is supplied (Requires Domain)" default="">
#<UDF name="domain" label="Domain" example="The domain for the DNS records: example.com (Requires API token)" default="">

# Spark
#<UDF name="spark_version" label="Which version of Apache Spark to install" oneOf="3.5.5">

# set force apt non-interactive
export DEBIAN_FRONTEND=noninteractive

# git repo
export GIT_REPO="https://github.com/akamai-compute-marketplace/apache-spark-occ.git"
export WORK_DIR="/tmp/marketplace-apache-spark-occ"
export RUN_DIR="/usr/local/bin/run"
export UUID=$(uuidgen | awk -F - '{print $1}')

# Debug and testing
# export BRANCH=""

# enable logging
exec > >(tee /dev/ttyS0 /var/log/stackscript.log) 2>&1

function cleanup {
  if [ "$?" != "0" ] || [ "$SUCCESS" == "true" ]; then
    cd ${HOME}
    if [ -d ${WORK_DIR} ]; then
      rm -rf ${WORK_DIR}
    fi
    if [ -f ${RUN_DIR} ]; then
      rm ${RUN_DIR}
    fi
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
        \"label\": \"${INSTANCE_PREFIX}1-${UUID}\"
      }" \
      https://api.linode.com/v4/linode/instances/${LINODE_ID}
}

function setup {
  # install dependencies
  export DEBIAN_FRONTEND=non-interactive
  apt-get update && apt-get upgrade -y
  apt-get install -y jq git python3 python3-pip python3-dev build-essential

  # rename provisioner and configure private IP if not present
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
  git clone ${GIT_REPO} ${WORK_DIR}
  # for a single testing branch
  # git clone -b ${BRANCH} ${GIT_REPO} ${WORK_DIR}

  # venv
  cd ${WORK_DIR}
  apt install python3-venv -y
  python3 -m venv env
  source env/bin/activate
  pip install pip --upgrade
  pip install -r requirements.txt
  ansible-galaxy install -r collections.yml
  # copy run script to path
  cp scripts/run.sh ${RUN_DIR}
  chmod +x ${RUN_DIR}
}

# main
setup
run build
run deploy && export SUCCESS="true"
if [ "${DEBUG}" == "NO" ]; then
  cleanup
fi
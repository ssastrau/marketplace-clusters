#!/bin/bash
# <APP> Marketplace App deploy StackScript.
# Template — replace <APP> / <app> and the UDF set with this app's fields.
# Canonical reference: deployment_scripts/linode-marketplace-hashicorp-nomad/hashicorp-nomad-deploy.sh

set -e
exec > >(tee /dev/ttyS0 /var/log/stackscript.log) 2>&1

# BEGIN CI-MODE
if [[ -n ${DEBUG} ]]; then trap "cleanup $? $LINENO" EXIT; fi
if [ "${MODE}" == "staging" ]; then
  trap "provision_failed $? $LINENO" ERR
else
  set -e
fi
# END CI-MODE

# <UDF name="user_name" label="The limited sudo user to be created for the Linode">
# <UDF name="disable_root" label="Disable root access over SSH?" oneOf="Yes,No" default="No">
# <UDF name="domain" label="Your domain" example="example.com" default="">
# <UDF name="subdomain" label="Subdomain" example="www" default="www">
# <UDF name="soa_email_address" label="Email for the SOA / Let's Encrypt" example="user@example.com" default="">
# --- add app-specific UDFs below ---

# BEGIN CI-GH
#GH_USER=""
#BRANCH=""
# git user and branch — set GH_USER + BRANCH to deploy from a fork/branch; defaults to upstream main
if [[ -n ${GH_USER} && -n ${BRANCH} ]]; then
  echo "[info] git user and branch set.."
  export GIT_REPO="https://github.com/${GH_USER}/marketplace-apps.git"
else
  export GH_USER="akamai-compute-marketplace"
  export BRANCH="main"
  export GIT_REPO="https://github.com/${GH_USER}/marketplace-apps.git"
fi
# END CI-GH

export WORK_DIR="/tmp/marketplace-apps"
export MARKETPLACE_APP="apps/linode-marketplace-<app>"
export DEBIAN_FRONTEND=noninteractive

function provision_failed {
  local exit_code=$1; local line=$2
  echo "[error] provisioning failed at line ${line} (exit ${exit_code})"
  # CI hook: report failure if MODE=staging
  exit "${exit_code}"
}

function cleanup {
  if [ -d "${WORK_DIR}" ]; then rm -rf "${WORK_DIR}"; fi
}

function udf {
  local group_vars="${WORK_DIR}/${MARKETPLACE_APP}/group_vars/linode/vars"
  sed 's/  //g' <<EOF > "${group_vars}"
username: ${USER_NAME}
EOF
  # boolean conversion — UDFs arrive as strings; Ansible needs real booleans
  if [ "${DISABLE_ROOT}" = "Yes" ]; then
    echo "disable_root: true" >> "${group_vars}"
  else
    echo "disable_root: false" >> "${group_vars}"
  fi
  [ -n "${DOMAIN}" ] && echo "domain: ${DOMAIN}" >> "${group_vars}"
  [ -n "${SUBDOMAIN}" ] && echo "subdomain: ${SUBDOMAIN}" >> "${group_vars}"
  [ -n "${SOA_EMAIL_ADDRESS}" ] && echo "soa_email_address: ${SOA_EMAIL_ADDRESS}" >> "${group_vars}"
  # --- append app-specific vars below ---
}

function run {
  apt-get update
  apt-get install -y git python3 python3-pip python3-venv
  git -C /tmp clone -b "${BRANCH}" "${GIT_REPO}"
  cd "${WORK_DIR}/${MARKETPLACE_APP}"
  python3 -m venv env
  # shellcheck disable=SC1091
  source env/bin/activate
  pip install -r requirements.txt
  ansible-galaxy install -r collections.yml
  udf
  export ANSIBLE_HOST_KEY_CHECKING=False
  ansible-playbook -v provision.yml && ansible-playbook -v site.yml
}

function installation_complete {
  echo "Installation complete. Credentials are in /home/${USER_NAME}/.credentials"
}

run
installation_complete
cleanup

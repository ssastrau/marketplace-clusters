#!/bin/bash

# enable logging
exec > >(tee /dev/ttyS0 /var/log/stackscript.log) 2>&1

# modes
#DEBUG="NO"
if [[ -n ${DEBUG} ]]; then
	if [ "${DEBUG}" == "NO" ]; then
		trap "cleanup $? $LINENO" EXIT
	fi
else
	trap "cleanup $? $LINENO" EXIT
fi

if [ "${MODE}" == "staging" ]; then
	trap "provision_failed $? $LINENO" ERR
else
	set -e
fi

##Linode/SSH security settings
#<UDF name="username" label="The limited sudo user to be created for the Linode: *All lowercase*">
#<UDF name="disable_root" label="Disable root access over SSH?" oneOf="Yes,No" default="No">
#<UDF name="add_ssh_keys" label="Add Account SSH Keys to All Nodes?" oneof="yes,no"  />

## Domain Settings
#<UDF name="token_password" label="Your Linode API token. This is needed to create your Jitsi cluster">
#<UDF name="subdomain" label="Subdomain" example="The subdomain for the DNS record: www (Requires Domain)" default="">
#<UDF name="domain" label="Domain" example="The domain for the DNS record: example.com (Requires API token)" default="">

## Let's Encrypt Settings
#<UDF name="soa_email_address" label="Admin Email for Let's Encrypt SSL certificate">

## OCC settings
# <UDF name="cluster_size" label="Jitsi cluster size" default="4" oneof="4,5,7" />

if [[ -n ${GH_USER} && -n ${BRANCH} ]]; then
	echo "[info] git user and branch set.."
	export GIT_REPO="https://github.com/${GH_USER}/marketplace-clusters.git"
else
	export GH_USER="akamai-compute-marketplace"
	export BRANCH="main"
	export GIT_REPO="https://github.com/${GH_USER}/marketplace-clusters.git"
fi

export WORK_DIR="/tmp/marketplace-clusters"
export MARKETPLACE_APP="apps/linode-marketplace-jitsi"

if [ -z "${UUID}" ]; then
	export UUID=$(uuidgen | awk -F - '{print $1}')
fi

function provision_failed {
	echo "[info] Provision failed. Sending status.."

	apt install jq -y

	local token=($(curl -ks -X POST ${KC_SERVER} \
		-H "Content-Type: application/json" \
		-d "{ \"username\":\"${KC_USERNAME}\", \"password\":\"${KC_PASSWORD}\" }" | jq -r .token))

	curl -sk -X POST ${DATA_ENDPOINT} \
		-H "Authorization: ${token}" \
		-H "Content-Type: application/json" \
		-d "{ \"app_label\":\"${APP_LABEL}\", \"status\":\"provision_failed\", \"branch\": \"${BRANCH}\", \
        \"gituser\": \"${GH_USER}\", \"runjob\": \"${RUNJOB}\", \"image\":\"${IMAGE}\", \
        \"type\":\"${TYPE}\", \"region\":\"${REGION}\", \"instance_env\":\"${INSTANCE_ENV}\" }"

	exit $?
}

function cleanup {
	if [ "$?" != "0" ]; then
		echo "PLAYBOOK FAILED. See /var/log/stackscript.log for details."
		echo "[info] Running Destroy playbook"
		destroy
	fi

	if [[ -f "${HOME}/.ssh/id_ansible_ed25519" || -f "${HOME}/.ssh/id_ansible_ed25519.pub" ]]; then
		echo "[info] Removing provisioner keys.."
		rm -f "${HOME}/.ssh/id_ansible_ed25519" "${HOME}/.ssh/id_ansible_ed25519.pub"
	fi

	if [ -d "${WORK_DIR}" ]; then
		echo "[info] Cleanup - Removing ${WORK_DIR}"
		rm -rf ${WORK_DIR}
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
		https://api.linode.com/v4/linode/instances/${LINODE_ID}/ips |
		jq -r '.ipv4.private[].address'
}

function configure_privateip {
	LINODE_IP=$(get_privateip)
	if [ ! -z "${LINODE_IP}" ]; then
		echo "[info] Linode private IP present"
	else
		echo "[warn] No private IP found. Adding.."
		add_privateip
		LINODE_IP=$(get_privateip)
		ip addr add ${LINODE_IP}/17 dev eth0 label eth0:1
	fi
}

function rename_provisioner {
	echo "[info] renaming the provisioner"
	curl -s -H "Content-Type: application/json" \
		-H "Authorization: Bearer ${TOKEN_PASSWORD}" \
		-X PUT -d "{
        \"label\": \"jitsi-instance-${UUID}\"
      }" \
		https://api.linode.com/v4/linode/instances/${LINODE_ID}
}

readonly TEMP_ROOT_PASS=$(openssl rand -base64 32)
readonly group_vars="${WORK_DIR}/${MARKETPLACE_APP}/group_vars/jitsi/vars"

function destroy {
	cd ${WORK_DIR}/${MARKETPLACE_APP}
	source env/bin/activate
	echo "[info] Destroying cluster nodes except provisioner..."
	ansible-playbook -v destroy.yml
}

function provisioner_sshkey {
	echo "[info] Creating provisioner SSH keys..."
	ssh-keygen -o -a 100 -t ed25519 -C "provisioner" -f "${HOME}/.ssh/id_ansible_ed25519" -q -N "" <<<y >/dev/null
	export PROVISIONER_SSH_PUB_KEY=$(cat ${HOME}/.ssh/id_ansible_ed25519.pub)
	export PROVISIONER_SSH_PRIV_KEY=$(cat ${HOME}/.ssh/id_ansible_ed25519)
	export SSH_KEY_PATH="${HOME}/.ssh/id_ansible_ed25519"
	chmod 700 ${HOME}/.ssh
	chmod 600 ${SSH_KEY_PATH}
	eval $(ssh-agent)
	ssh-add ${SSH_KEY_PATH}
	echo -e "\nprivate_key_file = ${SSH_KEY_PATH}" >>${WORK_DIR}/${MARKETPLACE_APP}/ansible.cfg
}

function provisioner_vars {
  local LINODE_PARAMS=($(curl -sH "Authorization: Bearer ${TOKEN_PASSWORD}" "https://api.linode.com/v4/linode/instances/${LINODE_ID}" | jq -r .type,.region,.image))
  local TAGS=$(curl -sH "Authorization: Bearer ${TOKEN_PASSWORD}" "https://api.linode.com/v4/linode/instances/${LINODE_ID}" | jq -r .tags)
	sed 's/  //g' <<EOF >${group_vars}
  # user vars
  uuid: ${UUID}
  ssh_keys: ${PROVISIONER_SSH_PUB_KEY}
  jvb_type: ${LINODE_PARAMS[0]}
  region: ${LINODE_PARAMS[1]}
  image: ${LINODE_PARAMS[2]}
  linode_tags: ${LINODE_TAGS}
  root_password: ${TEMP_ROOT_PASS}
  add_keys_prompt: ${ADD_SSH_KEYS}
EOF
}

function secrets {
  local SECRET_VARS_PATH="./group_vars/jitsi/secret_vars"
  local VAULT_PASS=$(openssl rand -base64 32)
  local PASSWORD=$(openssl rand -base64 32)
  echo "${VAULT_PASS}" > ./.vault-pass
  cat << EOF > ${SECRET_VARS_PATH}
`ansible-vault encrypt_string "${TEMP_ROOT_PASS}" --name 'root_pass'`
`ansible-vault encrypt_string "${TOKEN_PASSWORD}" --name 'api_token'`
`ansible-vault encrypt_string "${PASSWORD}" --name 'password'`
EOF
}

function udf {
	sed 's/  //g' <<EOF >>${group_vars}
  cluster_size: ${CLUSTER_SIZE}
  jitsi_count: 1

  username: ${USERNAME}
  soa_email_address: ${SOA_EMAIL_ADDRESS}
EOF

  if [ "$DISABLE_ROOT" = "Yes" ]; then
		echo "disable_root: yes" >>${group_vars}
	else
		echo "Leaving root login enabled"
	fi

	if [[ -n ${DOMAIN} ]]; then
		echo "[info] domain: ${DOMAIN}"
		echo "domain: ${DOMAIN}" >>${group_vars}
	else
		local default_dns
		default_dns="$(hostname -I | awk '{print $1}' | tr '.' '-' | awk '{print $1 ".ip.linodeusercontent.com"}')"
		echo "[info] subdomain not set, using default_dns: ${default_dns}"
		echo "default_dns: ${default_dns}" >>${group_vars}
	fi

	if [[ -n ${SUBDOMAIN} ]]; then
		echo "[info] subdomain: ${SUBDOMAIN}"
		echo "subdomain: ${SUBDOMAIN}" >>${group_vars}
	else
		echo "[info] subdomain not set, defaulting to: www"
		echo "subdomain: www" >>${group_vars}
	fi

	if [[ -n ${DEBUG} ]]; then
		echo "[info] debug ${DEBUG} passed"
		echo "debug: ${DEBUG}" >>${group_vars}
	fi

	if [ "${ADD_SSH_KEYS}" == "yes" ]; then
		echo "[info] Adding account SSH keys to authorized_keys..."
		curl -sH "Content-Type: application/json" \
			-H "Authorization: Bearer ${TOKEN_PASSWORD}" \
			https://api.linode.com/v4/profile/sshkeys | jq -r .data[].ssh_key >> /root/.ssh/authorized_keys
	fi

	# staging or production mode (ci)
	if [[ "${MODE}" == "staging" ]]; then
		echo "[info] running in staging mode..."
		echo "mode: ${MODE}" >>${group_vars}
	else
		echo "[info] running in production mode..."
		echo "mode: production" >>${group_vars}
	fi
}

function installation_complete {
	echo "Installation Complete!"
}

function run {
	# install dependencies
	export DEBIAN_FRONTEND=noninteractive
	apt-get update && apt-get upgrade -y
  apt-get install -y jq git python3 python3-pip python3-dev python3-venv build-essential

	# rename provisioner and configure private IP
	rename_provisioner
	configure_privateip

	# clone repo and set up Ansible environment
	echo "[info] Cloning ${BRANCH} branch from ${GIT_REPO}..."
	git -C /tmp clone -b ${BRANCH} ${GIT_REPO}
	cd ${WORK_DIR}/${MARKETPLACE_APP}
	python3 -m venv env
	source env/bin/activate
	pip install pip --upgrade
	pip install -r requirements.txt
	ansible-galaxy install -r collections.yml

	# populate group_vars
	provisioner_sshkey
	provisioner_vars
	secrets
	udf

	# run playbooks
	ansible-playbook -v provision.yml && ansible-playbook -v -i hosts site.yml
}

# main
run
installation_complete

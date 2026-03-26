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

## Deployment Variables
# <UDF name="token_password" label="Your Linode API token" />
# <UDF name="sudo_username" label="The limited sudo user to be created in the cluster" />
# <UDF name="email_address" label="Email Address" example="Example: user@domain.tld" />
# <UDF name="clusterheader" label="Cluster Settings" default="Yes" header="Yes">
# <UDF name="add_ssh_keys" label="Add Account SSH Keys to All Nodes?" oneof="yes,no"  default="yes" />
# <UDF name="cluster_size" label="Total instance count" default="6" oneof="6" />
# <UDF name="servers" label="Nomad Server count" default="3" oneOf="3" />
# <UDF name="clients" label="Nomad client size" default="3" oneof="3" />

if [[ -n ${GH_USER} && -n ${BRANCH} ]]; then
	echo "[info] git user and branch set.."
	export GIT_REPO="https://github.com/${GH_USER}/marketplace-clusters.git"
else
	export GH_USER="akamai-compute-marketplace"
	export BRANCH="main"
	export GIT_REPO="https://github.com/${GH_USER}/marketplace-clusters.git"
fi

export WORK_DIR="/tmp/marketplace-clusters"
export CLUSTER_APP="apps/linode-marketplace-nomad"
export CLIENT_APP="apps/linode-marketplace-nomad-client"

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
        \"label\": \"nomad-server-1-${UUID}\"
      }" \
		https://api.linode.com/v4/linode/instances/${LINODE_ID}
}

function tag_provisioner {
  echo "[info] tagging the provisioner"
  REGION=$(curl -sH "Authorization: Bearer ${TOKEN_PASSWORD}" "https://api.linode.com/v4/linode/instances/${LINODE_ID}" | jq -r .region)
  export REGION="${REGION}"
  curl -s -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${TOKEN_PASSWORD}" -X PUT \
    -d "{\"tags\": [\"${UUID}-${REGION}\"]}" \ \
    https://api.linode.com/v4/linode/instances/${LINODE_ID}
}

readonly NOMAD_VERSION='1.5.2'
readonly TEMP_ROOT_PASS=$(openssl rand -base64 32)
readonly VARS_PATH="./group_vars/nomad/vars"
readonly SECRET_VARS_PATH="./group_vars/nomad/secret_vars"

function destroy {
	cd ${WORK_DIR}/${CLUSTER_APP}
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
	echo -e "\nprivate_key_file = ${SSH_KEY_PATH}" >>${WORK_DIR}/${CLUSTER_APP}/ansible.cfg
}

function provisioner_vars {
  local LINODE_PARAMS=($(curl -sH "Authorization: Bearer ${TOKEN_PASSWORD}" "https://api.linode.com/v4/linode/instances/${LINODE_ID}" | jq -r .type,.region,.image))
  local TAGS=$(curl -sH "Authorization: Bearer ${TOKEN_PASSWORD}" "https://api.linode.com/v4/linode/instances/${LINODE_ID}" | jq -r .tags)
	sed 's/  //g' <<EOF >${VARS_PATH}
  # user vars
  uuid: ${UUID}
  ssh_keys: ${PROVISIONER_SSH_PUB_KEY}
  type: ${LINODE_PARAMS[0]}
  region: ${LINODE_PARAMS[1]}
  image: ${LINODE_PARAMS[2]}
  linode_tags: ${LINODE_TAGS}
  nomad_version: ${NOMAD_VERSION}
  cluster_uuid: ${UUID}-${LINODE_PARAMS[1]}
  cluster_mode: ${CLUSTER_MODE}
  cluster_size: ${CLUSTER_SIZE}
  servers: ${SERVERS}
  clients: ${CLIENTS}
EOF
}

function secrets {
  local VAULT_PASS=$(openssl rand -base64 32)
  echo "${VAULT_PASS}" > ./.vault-pass
  cat << EOF > ${SECRET_VARS_PATH}
`ansible-vault encrypt_string "${TEMP_ROOT_PASS}" --name 'root_pass'`
`ansible-vault encrypt_string "${TOKEN_PASSWORD}" --name 'api_token'`
EOF
}

function udf {
	sed 's/  //g' <<EOF >>${VARS_PATH}
  sudo_username: ${SUDO_USERNAME}
  email_address: ${EMAIL_ADDRESS}
  add_keys_prompt: ${ADD_SSH_KEYS}
EOF

	if [[ -n ${DEBUG} ]]; then
		echo "[info] debug ${DEBUG} passed"
		echo "debug: ${DEBUG}" >>${VARS_PATH}
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
		echo "mode: ${MODE}" >>${VARS_PATH}
	else
		echo "[info] running in production mode..."
		echo "mode: production" >>${VARS_PATH}
	fi
}

function installation_complete {
	echo "Installation Complete!"
}

function run {
	# install dependencies
	export DEBIAN_FRONTEND=noninteractive
	apt-get update && apt-get upgrade -y
	apt-get install -y jq git python3 python3-pip python3-venv build-essential firewalld

	# rename provisioner and configure private IP
	rename_provisioner
	tag_provisioner
	configure_privateip

	# clone repo and set up Ansible environment
	echo "[info] Cloning ${BRANCH} branch from ${GIT_REPO}..."
	git -C /tmp clone -b ${BRANCH} ${GIT_REPO}
	cd ${WORK_DIR}/${CLUSTER_APP}
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
	ansible-playbook -v provision.yml

	# deploy cluster nodes
	echo "[info] configuring nomad cluster"
	ansible-playbook -v -i hosts site.yml --extra-vars "cluster_mode='cluster'"

	# deploy client nodes
	echo "[info] configuring nomad clients"
	cd ../../${CLIENT_APP}
  cp ../../${CLUSTER_APP}/${VARS_PATH} ${VARS_PATH}
  cp ../../${CLUSTER_APP}/${SECRET_VARS_PATH} ${SECRET_VARS_PATH}
  cp ../../${CLUSTER_APP}/hosts ./hosts
  cp ../../${CLUSTER_APP}/.vault-pass .
	ansible-playbook -v -i hosts site.yml --extra-vars "cluster_mode='client' is_provisioner='false' --tags cluster"
}

# main
run
installation_complete

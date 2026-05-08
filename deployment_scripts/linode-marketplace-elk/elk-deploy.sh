#!/bin/bash
# STACKSCRIPT_ID: 1966222

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

# cleanup will always happen. If DEBUG is passed and is anything
# other than NO, it will always trigger cleanup. This is useful for
# ci testing and passing vars to the instance.

if [ "${MODE}" == "staging" ]; then
	trap "provision_failed $? $LINENO" ERR
else
	set -e
fi

## Linode/SSH Security Settings
#<UDF name="token_password" label="Your Linode API token" />
#<UDF name="soa_email_address" label="Email address (for the Let's Encrypt SSL certificate)" example="Example: user@example.com">
#<UDF name="user_name" label="The limited sudo user to be created for the Linode: *No Capital Letters or Special Characters*">
#<UDF name="disable_root" label="Disable root access over SSH?" oneOf="Yes,No" default="No">

## Domain Settings
#<UDF name="subdomain" label="Subdomain" example="The subdomain for the DNS record. `www` will be entered if no subdomain is supplied (Requires Domain)" default="">
#<UDF name="domain" label="Domain" example="The domain for the DNS record: example.com (Requires API token)" default="">

# ELK Settings #
#<UDF name="clusterheader" label="Cluster Settings" default="Yes" header="Yes">

# Cluster name
#<UDF name="cluster_name" label="Cluster Name" example="Example: ELK" default="ELK Stack">

# Kibana size
#<UDF name="cluster_size" label="Kibana Size" oneOf="1" default="1">

# Cluster size ($prefix_cluster_size):
#<UDF name="elasticsearch_cluster_size" label="Elasticsearch Cluster Size" oneOf="2,4,6,8,10,12,14" default="2">
#<UDF name="logstash_cluster_size" label="Logstash Cluster Size" oneOf="2,4,6,8,10,12,14" default="2">

# Instance types ($prefix_cluster_type):
#<UDF name="elasticsearch_cluster_type" label="Elasticsearch Instance Type" oneOf="Dedicated 4GB,Dedicated 8GB,Dedicated 16GB,Dedicated 32GB,Dedicated 64GB,Dedicated 96GB,Dedicated 128GB,Dedicated 256GB" default="Dedicated 4GB">
#<UDF name="logstash_cluster_type" label="Logstash Instance Type" oneOf="Dedicated 4GB,Dedicated 8GB,Dedicated 16GB,Dedicated 32GB,Dedicated 64GB,Dedicated 96GB,Dedicated 128GB,Dedicated 256GB" default="Dedicated 4GB">

#<UDF name="beats_allow" label="Filebeat IP addresses allowed to access Logstash" example="Example: 192.0.2.21/32, 198.51.100.17/24" default="">

#<UDF name="logstash_ingest_username" label="Logstash username to be created for indices." example="Example: logstash_ingest" default="">

#<UDF name="elasticsearch_index_name" label="Elasticsearch index to be created for log ingestion" example="Example: wordpress-logs" default="">

# SSL vars

# <UDF name="sslheader" label="SSL Information" header="Yes" default="Yes" required="Yes">
# <UDF name="country_name" label="Details for self-signed SSL certificates: Country or Region" oneof="AD,AE,AF,AG,AI,AL,AM,AO,AQ,AR,AS,AT,AU,AW,AX,AZ,BA,BB,BD,BE,BF,BG,BH,BI,BJ,BL,BM,BN,BO,BQ,BR,BS,BT,BV,BW,BY,BZ,CA,CC,CD,CF,CG,CH,CI,CK,CL,CM,CN,CO,CR,CU,CV,CW,CX,CY,CZ,DE,DJ,DK,DM,DO,DZ,EC,EE,EG,EH,ER,ES,ET,FI,FJ,FK,FM,FO,FR,GA,GB,GD,GE,GF,GG,GH,GI,GL,GM,GN,GP,GQ,GR,GS,GT,GU,GW,GY,HK,HM,HN,HR,HT,HU,ID,IE,IL,IM,IN,IO,IQ,IR,IS,IT,JE,JM,JO,JP,KE,KG,KH,KI,KM,KN,KP,KR,KW,KY,KZ,LA,LB,LC,LI,LK,LR,LS,LT,LU,LV,LY,MA,MC,MD,ME,MF,MG,MH,MK,ML,MM,MN,MO,MP,MQ,MR,MS,MT,MU,MV,MW,MX,MY,MZ,NA,NC,NE,NF,NG,NI,NL,NO,NP,NR,NU,NZ,OM,PA,PE,PF,PG,PH,PK,PL,PM,PN,PR,PS,PT,PW,PY,QA,RE,RO,RS,RU,RW,SA,SB,SC,SD,SE,SG,SH,SI,SJ,SK,SL,SM,SN,SO,SR,SS,ST,SV,SX,SY,SZ,TC,TD,TF,TG,TH,TJ,TK,TL,TM,TN,TO,TR,TT,TV,TW,TZ,UA,UG,UM,US,UY,UZ,VA,VC,VE,VG,VI,VN,VU,WF,WS,YE,YT,ZA,ZM,ZW" />
# <UDF name="state_or_province_name" label="State or Province" example="Example: Pennsylvania" />
# <UDF name="locality_name" label="Locality" example="Example: Philadelphia" />
# <UDF name="organization_name" label="Organization" example="Example: Akamai Technologies" />
# <UDF name="email_address" label="Email Address" example="Example: user@example.com" />
# <UDF name="ca_common_name" label="CA Common Name" example="Example: Elasticsearch CA" />

# GIT REPO #

#GH_USER=""
#BRANCH=""
# git user and branch
if [[ -n ${GH_USER} && -n ${BRANCH} ]]; then
	echo "[info] git user and branch set.."
	export GIT_REPO="https://github.com/${GH_USER}/marketplace-clusters.git"
else
	export GH_USER="akamai-compute-marketplace"
	export BRANCH="main"
	export GIT_REPO="https://github.com/${GH_USER}/marketplace-clusters.git"
fi

export WORK_DIR="/tmp/marketplace-clusters"
export MARKETPLACE_APP="apps/linode-marketplace-elk"

if [ -z "${UUID}" ]; then
  export UUID=$(uuidgen | awk -F - '{print $1}')
fi

function provision_failed {
	echo "[info] Provision failed. Sending status.."

	# dep
	apt install jq -y

	# set token
	local token=($(curl -ks -X POST ${KC_SERVER} \
		-H "Content-Type: application/json" \
		-d "{ \"username\":\"${KC_USERNAME}\", \"password\":\"${KC_PASSWORD}\" }" | jq -r .token))

	# send pre-provision failure
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

	# provisioner keys
	if [[ -f "${HOME}/.ssh/id_ansible_ed25519" || -f "${HOME}/.ssh/id_ansible_ed25519.pub" ]]; then
		echo "[info] Removing provisioner keys.."
		rm -f "${HOME}/.ssh/id_ansible_ed25519" "${HOME}/.ssh/id_ansible_ed25519.pub"
	fi

	if [ -d "${WORK_DIR}" ]; then
		echo "[info] Cleanup - Removing ${WORK_DIR}"
		rm -rf ${WORK_DIR}
	fi
}

# INSTANCE SETUP #

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
	INSTANCE_PREFIX=$(curl -sH "Authorization: Bearer ${TOKEN_PASSWORD}" "https://api.linode.com/v4/linode/instances/${LINODE_ID}" | jq -r .label)
	export INSTANCE_PREFIX="${INSTANCE_PREFIX}"
	echo "[info] renaming the provisioner"
	curl -s -H "Content-Type: application/json" \
		-H "Authorization: Bearer ${TOKEN_PASSWORD}" \
		-X PUT -d "{
        \"label\": \"kibana-${UUID}\"
      }" \
		https://api.linode.com/v4/linode/instances/${LINODE_ID}
}

# PROVISIONER SETUP

readonly TEMP_ROOT_PASS=$(openssl rand -base64 32)
readonly LINODE_PARAMS=($(curl -sH "Authorization: Bearer ${TOKEN_PASSWORD}" "https://api.linode.com/v4/linode/instances/${LINODE_ID}" | jq -r .type,.region,.image,.disk_encryption))
readonly TAGS=$(curl -sH "Authorization: Bearer ${TOKEN_PASSWORD}" "https://api.linode.com/v4/linode/instances/${LINODE_ID}" | jq -r .tags)
#readonly VARS_PATH="./group_vars/linode/vars"
readonly group_vars="${WORK_DIR}/${MARKETPLACE_APP}/group_vars/linode/vars"

# destroys all instances except provisioner node
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
	# Adds variables to configure cluster instances.
	sed 's/  //g' <<EOF >${group_vars}
  # provisioner vars
  provisioner_ssh_pubkey: "${PROVISIONER_SSH_PUB_KEY}"
  provisioner: kibana-${UUID}
  provisioner_prefix: ${INSTANCE_PREFIX}
  type: ${LINODE_PARAMS[0]}
  region: ${LINODE_PARAMS[1]}
  image: ${LINODE_PARAMS[2]}
  disk_encryption: ${LINODE_PARAMS[3]}
  linode_tags: ${TAGS}
  uuid: ${UUID}
  token_password: ${TOKEN_PASSWORD}
  temp_root_pass: ${TEMP_ROOT_PASS}
EOF
}

# UDF SETUP

function udf {
	sed 's/  //g' <<EOF >>${group_vars}
  # sudo username
  username: ${USER_NAME}

  # SSL
  country_name: ${COUNTRY_NAME}
  state_or_province_name: ${STATE_OR_PROVINCE_NAME}
  locality_name: ${LOCALITY_NAME}
  organization_name: ${ORGANIZATION_NAME}
  email_address: ${EMAIL_ADDRESS}
  ca_common_name: ${CA_COMMON_NAME}

  # Certbot
  soa_email_address: ${SOA_EMAIL_ADDRESS}
EOF

	if [ "$DISABLE_ROOT" = "Yes" ]; then
		echo "disable_root: yes" >>${group_vars}
	else
		echo "Leaving root login enabled"
	fi
	if [[ -n ${DOMAIN} ]]; then
		echo "domain: ${DOMAIN}" >>${group_vars}
	else
		echo "default_dns: $(hostname -I | awk '{print $1}' | tr '.' '-' | awk {'print $1 ".ip.linodeusercontent.com"'})" >>${group_vars}
	fi
	if [[ -n ${SUBDOMAIN} ]]; then
		echo "subdomain: ${SUBDOMAIN}" >>${group_vars}
	else
		echo "subdomain: www" >>${group_vars}
	fi
	if [[ -n ${DEBUG} ]]; then
		echo "[info] debug ${DEBUG} passed"
		echo "debug: ${DEBUG}" >>${group_vars}
	fi

	# ELK vars

	if [[ -n ${CLUSTER_NAME} ]]; then
		echo "cluster_name: ${CLUSTER_NAME}" >>${group_vars}
	fi
	if [[ -n ${CLUSTER_SIZE} ]]; then
		echo "kibana_cluster_size: ${CLUSTER_SIZE}" >>${group_vars}
	fi
	if [[ -n ${ELASTICSEARCH_CLUSTER_SIZE} ]]; then
		echo "elasticsearch_cluster_size: ${ELASTICSEARCH_CLUSTER_SIZE}" >>${group_vars}
	fi
	if [[ -n ${LOGSTASH_CLUSTER_SIZE} ]]; then
		echo "logstash_cluster_size: ${LOGSTASH_CLUSTER_SIZE}" >>${group_vars}
	fi
	if [[ -n ${ELASTICSEARCH_CLUSTER_TYPE} ]]; then
		echo "elasticsearch_cluster_type: ${ELASTICSEARCH_CLUSTER_TYPE}" >>${group_vars}
	fi
	if [[ -n ${LOGSTASH_CLUSTER_TYPE} ]]; then
		echo "logstash_cluster_type: ${LOGSTASH_CLUSTER_TYPE}" >>${group_vars}
	fi
	if [[ -z ${BEATS_ALLOW} ]]; then
		echo "[info] No IP addresses provided for beat"
	else
		echo "beats_allow: [${BEATS_ALLOW}]" >>${group_vars}
	fi
	if [[ -n ${LOGSTASH_INGEST_USERNAME} ]]; then
		echo "logstash_ingest_username: ${LOGSTASH_INGEST_USERNAME}" >>${group_vars}
	fi
	if [[ -n ${ELASTICSEARCH_INDEX_NAME} ]]; then
		echo "elasticsearch_index_name: ${ELASTICSEARCH_INDEX_NAME}" >>${group_vars}
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

# COMPLETE
function installation_complete {
	echo "Installation Complete!"
}

# MAIN

function run {
	# install dependencies
	export DEBIAN_FRONTEND=noninteractive
	apt-get update && apt-get upgrade -y
	apt-get install -y jq git python3 python3-pip python3-venv

	# add private IP address
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
	udf

	# update plan label with plan typeId
	python3 plan_typeid.py

	# run playbooks
	ansible-playbook -v provision.yml && ansible-playbook -v -i hosts site.yml
}

# main
run
installation_complete

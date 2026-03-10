#!/bin/bash

DEFAULT_DNS="$(hostname -I | awk '{print $1}'| tr '.' '-' | awk {'print $1 ".ip.linodeusercontent.com"'})"

# custom env variables from cli
if [[ -n ${INSTANCE_ENV} ]]; then
  custom_vars=(${INSTANCE_ENV})
  var_count=${#custom_vars[@]}
  count=0
  while [ ${count} -lt ${var_count} ]; do
    export ${custom_vars[count]}
  count=$(( $count + 1 ))
  done
fi

# UDF Variables

declare -A UDF_VARS

if [[ -n "${USER_NAME}" ]]; then
        UDF_VARS["USER_NAME"]="${USER_NAME}"
else
        UDF_VARS["USER_NAME"]="admin" # default
fi

if [[ -n "${DISABLE_ROOT}" ]]; then
        UDF_VARS["DISABLE_ROOT"]="${DISABLE_ROOT}"
else
        UDF_VARS["DISABLE_ROOT"]="No" # default
fi

if [[ -n "${TOKEN_PASSWORD}" ]]; then
        UDF_VARS["TOKEN_PASSWORD"]="${TOKEN_PASSWORD}"
elif [[ -n "${LINODE_API_SECRET}" ]]; then
        UDF_VARS["TOKEN_PASSWORD"]="${LINODE_API_SECRET}"
else
        UDF_VARS["TOKEN_PASSWORD"]="HugsAreWorthMoreThanHandshakes" # default
fi

if [[ -n "${SOA_EMAIL_ADDRESS}" ]]; then
        UDF_VARS["SOA_EMAIL_ADDRESS"]="${SOA_EMAIL_ADDRESS}"
else
        UDF_VARS["SOA_EMAIL_ADDRESS"]="webmaster@${DEFAULT_DNS}" # default
fi

if [[ -n "${SUDO_USERNAME}" ]]; then
        UDF_VARS["SUDO_USERNAME"]="${SUDO_USERNAME}"
else
        UDF_VARS["SUDO_USERNAME"]="admin" # default
fi

if [[ -n "${ADD_SSH_KEYS}" ]]; then
        UDF_VARS["ADD_SSH_KEYS"]="${ADD_SSH_KEYS}"
else
        UDF_VARS["ADD_SSH_KEYS"]="yes" # default
fi

if [[ -n "${DOMAIN}" ]]; then
        UDF_VARS["DOMAIN"]="${DOMAIN}"
else
        UDF_VARS["DOMAIN"]="" # default
fi

if [[ -n "${SUBDOMAIN}" ]]; then
        UDF_VARS["SUBDOMAIN"]="${SUBDOMAIN}"
else
        UDF_VARS["SUBDOMAIN"]="" # default
fi

if [[ -n "${CLUSTER_NAME}" ]]; then
        UDF_VARS["CLUSTER_NAME"]="${CLUSTER_NAME}"
else
        UDF_VARS["CLUSTER_NAME"]="Apache Spark" # default
fi

if [[ -n "${CLUSTER_SIZE}" ]]; then
        UDF_VARS["CLUSTER_SIZE"]="${CLUSTER_SIZE}"
else
        UDF_VARS["CLUSTER_SIZE"]="3" # default
fi

if [[ -n "${SPARK_VERSION}" ]]; then
        UDF_VARS["SPARK_VERSION"]="${SPARK_VERSION}"
else
        UDF_VARS["SPARK_VERSION"]="3.5.8" # default
fi

if [[ -n "${SPARK_USER}" ]]; then
        UDF_VARS["SPARK_USER"]="${SPARK_USER}"
else
        UDF_VARS["SPARK_USER"]="spark" # default
fi

set_vars() {
  for key in "${!UDF_VARS[@]}"; do
    export "${key}"="${UDF_VARS[$key]}"
    echo "[info] ${key}=${UDF_VARS[$key]}"
  done
}

# main
set_vars
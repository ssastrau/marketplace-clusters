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

if [[ -n "${COUNTRY_NAME}" ]]; then
        UDF_VARS["COUNTRY_NAME"]="${COUNTRY_NAME}"
else
        UDF_VARS["COUNTRY_NAME"]="US" # default
fi

if [[ -n "${STATE_OR_PROVINCE_NAME}" ]]; then
        UDF_VARS["STATE_OR_PROVINCE_NAME"]="${STATE_OR_PROVINCE_NAME}"
else
        UDF_VARS["STATE_OR_PROVINCE_NAME"]="Pennsylvania" # default
fi

if [[ -n "${LOCALITY_NAME}" ]]; then
        UDF_VARS["LOCALITY_NAME"]="${LOCALITY_NAME}"
else
        UDF_VARS["LOCALITY_NAME"]="Philadelphia" # default
fi

if [[ -n "${ORGANIZATION_NAME}" ]]; then
        UDF_VARS["ORGANIZATION_NAME"]="${ORGANIZATION_NAME}"
else
        UDF_VARS["ORGANIZATION_NAME"]="Akamai Technologies" # default
fi

if [[ -n "${EMAIL_ADDRESS}" ]]; then
        UDF_VARS["EMAIL_ADDRESS"]="${EMAIL_ADDRESS}"
else
        UDF_VARS["EMAIL_ADDRESS"]="user@example.com" # default
fi

if [[ -n "${CA_COMMON_NAME}" ]]; then
        UDF_VARS["CA_COMMON_NAME"]="${CA_COMMON_NAME}"
else
        UDF_VARS["CA_COMMON_NAME"]="Elasticsearch CA" # default
fi

if [[ -n "${CLUSTER_NAME}" ]]; then
        UDF_VARS["CLUSTER_NAME"]="${CLUSTER_NAME}"
else
        UDF_VARS["CLUSTER_NAME"]="ELK Stack" # default
fi

if [[ -n "${CLUSTER_SIZE}" ]]; then
        UDF_VARS["CLUSTER_SIZE"]="${CLUSTER_SIZE}"
else
        UDF_VARS["CLUSTER_SIZE"]="1" # default
fi

if [[ -n "${ELASTICSEARCH_CLUSTER_SIZE}" ]]; then
        UDF_VARS["ELASTICSEARCH_CLUSTER_SIZE"]="${ELASTICSEARCH_CLUSTER_SIZE}"
else
        UDF_VARS["ELASTICSEARCH_CLUSTER_SIZE"]="2" # default
fi

if [[ -n "${LOGSTASH_CLUSTER_SIZE}" ]]; then
        UDF_VARS["LOGSTASH_CLUSTER_SIZE"]="${LOGSTASH_CLUSTER_SIZE}"
else
        UDF_VARS["LOGSTASH_CLUSTER_SIZE"]="2" # default
fi

if [[ -n "${ELASTICSEARCH_CLUSTER_TYPE}" ]]; then
        UDF_VARS["ELASTICSEARCH_CLUSTER_TYPE"]="${ELASTICSEARCH_CLUSTER_TYPE}"
else
        UDF_VARS["ELASTICSEARCH_CLUSTER_TYPE"]="Dedicated 4GB" # default
fi

if [[ -n "${LOGSTASH_CLUSTER_TYPE}" ]]; then
        UDF_VARS["LOGSTASH_CLUSTER_TYPE"]="${LOGSTASH_CLUSTER_TYPE}"
else
        UDF_VARS["LOGSTASH_CLUSTER_TYPE"]="Dedicated 4GB" # default
fi

if [[ -n "${BEATS_ALLOW}" ]]; then
        UDF_VARS["BEATS_ALLOW"]="${BEATS_ALLOW}"
else
        UDF_VARS["BEATS_ALLOW"]="" # default
fi

if [[ -n "${LOGSTASH_INGEST_USERNAME}" ]]; then
        UDF_VARS["LOGSTASH_INGEST_USERNAME"]="${LOGSTASH_INGEST_USERNAME}"
else
        UDF_VARS["LOGSTASH_INGEST_USERNAME"]="" # default
fi

if [[ -n "${ELASTICSEARCH_INDEX_NAME}" ]]; then
        UDF_VARS["ELASTICSEARCH_INDEX_NAME"]="${ELASTICSEARCH_INDEX_NAME}"
else
        UDF_VARS["ELASTICSEARCH_INDEX_NAME"]="" # default
fi

set_vars() {
  for key in "${!UDF_VARS[@]}"; do
    export "${key}"="${UDF_VARS[$key]}"
  done
}

# main
set_vars

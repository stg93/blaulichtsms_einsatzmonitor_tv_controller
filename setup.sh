#!/bin/bash
# Auto setup script for alarmmonitor
set -eo pipefail

if [[ -n "$TRACE" ]]; then
  set -x
fi

GITHUB_USER=${GITHUB_USER:-"stg93"}
GITHUB_BRANCH=${GITHUB_BRANCH:-"master"}
GITHUB_REPO_NAME=${GITHUB_REPO_NAME:-"blaulichtsms_einsatzmonitor_tv_controller"}
GITHUB_DOWNLOAD_URL="https://github.com/${GITHUB_USER}/${GITHUB_REPO_NAME}/archive/${GITHUB_BRANCH}.zip"
GITHUB_REPO="https://github.com/${GITHUB_USER}/${GITHUB_REPO_NAME}.git"

echo
echo "Installing dependencies"
sudo apt update && sudo apt -y install git cec-utils
sudo pip3 install --system "requests" "cec" "pyyaml"

echo
echo "cloning alarmmonitor from Github"
git clone -b "${GITHUB_BRANCH}" "${GITHUB_REPO}"
cd "${GITHUB_REPO_NAME}"

echo "Configuring alarmmonitor"
if [[ -f "../config.ini" ]]; then
  echo "Using predefined config"
  cp ../config.ini ./
  echo "Setting service user to ${USER}"
  sed -i "s|User=.*|User=${USER}|g" alarmmonitor.service
else
  python3 configure.py
fi

echo "Installing alarmmonitor"
sudo ./INSTALL

#!/bin/bash
# Auto setup script for alarmmonitor
set -eo pipefail

GITHUB_USER=${GITHUB_USER:-"stg93"}
GITHUB_BRANCH=${GITHUB_BRANCH:-"master"}
GITHUB_REPO_NAME=${GITHUB_REPO_NAME:-"blaulichtsms_einsatzmonitor_tv_controller"}
GITHUB_REPO="https://github.com/${GITHUB_USER}/${GITHUB_REPO_NAME}.git"

echo
echo "Installing dependencies"
# configure.py needs requests and yaml, INSTALL takes care of all other dependencies
sudo apt-get update && sudo apt-get -y install git python3-requests python3-yaml

echo
if [[ -d "${GITHUB_REPO_NAME}/.git" ]]; then
  echo "Updating existing alarmmonitor checkout to ${GITHUB_USER}/${GITHUB_BRANCH}"
  cd "${GITHUB_REPO_NAME}"
  git remote set-url origin "${GITHUB_REPO}"
  git fetch origin "${GITHUB_BRANCH}"
  git checkout -B "${GITHUB_BRANCH}" "origin/${GITHUB_BRANCH}"
else
  echo "Cloning alarmmonitor from Github (${GITHUB_USER}/${GITHUB_BRANCH})"
  git clone -b "${GITHUB_BRANCH}" "${GITHUB_REPO}"
  cd "${GITHUB_REPO_NAME}"
fi

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

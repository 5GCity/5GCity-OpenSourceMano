#!/bin/bash
REPOSITORY_BASE=https://osm-download.etsi.org/repository/osm/debian
RELEASE=ReleaseFOUR
REPOSITORY=testing

add_repo() {
  REPO_CHECK="^$1"
  grep "${REPO_CHECK/\[arch=amd64\]/\\[arch=amd64\\]}" /etc/apt/sources.list > /dev/null 2>&1
  if [ $? -ne 0 ]
  then
    wget -qO - $REPOSITORY_BASE/$RELEASE/OSM%20ETSI%20Release%20Key.gpg | sudo apt-key add -
    sudo DEBIAN_FRONTEND=noninteractive add-apt-repository -y "$1" && sudo DEBIAN_FRONTEND=noninteractive apt-get update
    return 0
  fi

  return 1
}

add_repo "deb [arch=amd64] $REPOSITORY_BASE/$RELEASE $REPOSITORY devops"
sudo DEBIAN_FRONTEND=noninteractive  apt-get install osm-devops
/usr/share/osm-devops/installers/full_install_osm.sh -R $RELEASE -r $REPOSITORY -D /usr/share/osm-devops "$@"

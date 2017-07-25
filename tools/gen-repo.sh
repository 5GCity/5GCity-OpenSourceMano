#!/bin/bash

function usage() {
    echo -e "usage: $0 [OPTIONS] BUILD"
    echo -e "  OPTIONS"
    echo -e "  -p  <passphrase file>:   gpg passphrase file"
    echo -e "  -i  <incoming repo>      "
    echo -e "  -o  <outgoing repo>      "
    echo -e "  -k  <gpg key>            "
    echo -e "  -j  <jfrog cli>          "
    echo -e "  -d  <base dir>           "
    exit 1
}

[ $# -lt 1 ] && usage

BUILD="$1"

function FATAL() {
    echo -e $1
    exit 1
}

IN_REPO="unstable"
OUT_REPO="stable"
GPGKEY=71C0472C
JFROG_CLI=~/jfrog
REPO_BASE=repo
BASE_DIR=$REPO_BASE/osm/debian/ReleaseTWO
CURR_DIR=$(pwd)

while getopts ":p:i:o:k:j::d:" o; do
    case "${o}" in
        p)
            PASSPHRASE_FILE=${OPTARG}
            ;;
        i)
            IN_REPO=${OPTARG}
            ;;
        o)
            OUT_REPO=${OPTARG}
            ;;
        k)
            GPGKEY=${OPTARG}
            ;;
        j)
            JFROG_CLI=${OPTARG}
            ;;
        d)
            BASE_DIR=${OPTARG}
            ;;
        *)
            usage
            exit 1
            ;;
    esac
done

[ -x $JFROG_CLI ] || FATAL "jfrog cli not found. Please install https://www.jfrog.com/getcli/ and use option '-j <jfrog cli location>'"

$JFROG_CLI rt download --build "$BUILD" osm-release || FATAL "Failed to download"

BUILD_NUMBER=$(basename "$BUILD")

[ $PASSPHRASE_FILE ] && GPG_PASSPHRASE="--no-use-agent --passphrase \"$(cat $PASSPHRASE_FILE)\""

mkdir -p $BASE_DIR/dists

cp -R $BUILD_NUMBER/dists/$IN_REPO $BASE_DIR/dists/$OUT_REPO
cp -R $BUILD_NUMBER/pool $BASE_DIR/

cd $BASE_DIR

for i in RO osmclient openvim SO UI; do

    # gpg sign the packages
    dpkg-sig -g "$GPG_PASSPHRASE" -k $GPGKEY --sign builder pool/$i/*.deb

    # mkdir -p dists/stable/$i/binary-amd64/
    apt-ftparchive packages pool/$i > dists/$OUT_REPO/$i/binary-amd64/Packages
    rm -f dists/$OUT_REPO/$i/binary-amd64/Packages.gz
    gzip -9fk dists/$OUT_REPO/$i/binary-amd64/Packages
done

# Generate the root Release
# pushd dists/
apt-ftparchive release dists/$OUT_REPO > dists/$OUT_REPO/Release
#gzip -9fk dists/$OUT_REPO/Release

rm -f dists/$OUT_REPO/InRelease
eval gpg $GPG_PASSPHRASE --default-key $GPGKEY --clearsign -o dists/$OUT_REPO/InRelease dists/$OUT_REPO/Release

rm -f dists/$OUT_REPO/Release.gpg
eval gpg $GPG_PASSPHRASE --default-key $GPGKEY -abs -o dists/$OUT_REPO/Release.gpg dists/$OUT_REPO/Release


echo "performing rsync to osm-download.etsi.org:/repos/"
cd $CURR_DIR/$REPO_BASE

rsync -avR . rsync://osmusers@osm-download.etsi.org/repos/

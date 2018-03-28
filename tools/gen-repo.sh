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
    echo -e "  -b  <build>              "
    echo -e "  -r  <release dir>        "
    echo -e "  -h  <rsync user@host>    "
    echo -e "  -R  <rsync options>      "
    echo -e "  -P  <public key file>    "
    echo -e "  -c  <changelogfile>      "
    echo -e "  -m  <MDG repos>          "
    exit 1
}

function FATAL() {
    echo -e $1
    exit 1
}

function dump_vars() {
    echo "incoming repo:  $IN_REPO"
    echo "outgoing repo:  $OUT_REPO"
    echo "GPGKEY:         $GPGKEY"
    echo "JFROG_CLI:      $JFROG_CLI"
    echo "REPO_BASE:      $REPO_BASE"
    echo "RELEASE_DIR:    $RELEASE_DIR"
    echo "BUILD:          $BUILD"
    echo "RSYNC_USER_HOST $RSYNC_USER_HOST"
    echo "RSYNC_OPTIONS   $RSYNC_OPTIONS"
    echo "PUBLIC_KEY_FILE $PUBLIC_KEY_FILE"
    echo "BUILD:          $BUILD"
    echo "BUILD_NUMBER:   $BUILD_NUMBER"
}

MDG_REPOS="RO osmclient openvim SO UI IM devops MON"
IN_REPO="unstable"
OUT_REPO="stable"
GPGKEY=71C0472C
JFROG_CLI=~/jfrog
REPO_BASE=repo
RELEASE_DIR=ReleaseTWO
RSYNC_USER_HOST=osmusers@osm-download.etsi.org
CURR_DIR=$(pwd)
PUBLIC_KEY_FILE=~/OSM\ ETSI\ Release\ Key.gpg
CHANGE_LOG_FILE=

while getopts ":p:i:o:k:j::d:b:r:h:R:P:c:m:" o; do
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
        b)
            BUILD=${OPTARG}
            ;;
        r)
            RELEASE_DIR=${OPTARG}
            ;;
        h)
            RSYNC_USER_HOST=${OPTARG}
            ;;
        R)
            RSYNC_OPTIONS=${OPTARG}
            ;;
        P)
            PUBLIC_KEY_FILE=${OPTARG}
            ;;
        c)
            CHANGE_LOG_FILE=${OPTARG}
            ;;
        m)
            MDG_REPOS=${OPTARG}
            ;;
        *)
            usage
            exit 1
            ;;
    esac
done

BASE_DIR=$REPO_BASE/osm/debian/$RELEASE_DIR

[ -z "$BUILD" ] && FATAL "missing option: -b <build>"

BUILD_NUMBER=$(echo "$BUILD" | sed -e 's/.*:: //g')

dump_vars

[ -x $JFROG_CLI ] || FATAL "jfrog cli not found. Please install https://www.jfrog.com/getcli/ and use option '-j <jfrog cli location>'"

$JFROG_CLI rt download --build "$BUILD" osm-release || FATAL "Failed to download"


[ $PASSPHRASE_FILE ] && GPG_PASSPHRASE="--no-tty --no-use-agent --passphrase \"$(cat $PASSPHRASE_FILE)\""

mkdir -p $BASE_DIR/dists

cp -R $BUILD_NUMBER/dists/$IN_REPO $BASE_DIR/dists/$OUT_REPO
cp -R $BUILD_NUMBER/pool $BASE_DIR/

echo "copy changelog from $BUILD_NUMBER/changelog to $BASE_DIR/"
cp -R $BUILD_NUMBER/changelog $BASE_DIR/

cd $BASE_DIR

for i in $MDG_REPOS; do

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
eval gpg $GPG_PASSPHRASE --no-tty --default-key $GPGKEY --clearsign -o dists/$OUT_REPO/InRelease dists/$OUT_REPO/Release

rm -f dists/$OUT_REPO/Release.gpg
eval gpg $GPG_PASSPHRASE --no-tty --default-key $GPGKEY -abs -o dists/$OUT_REPO/Release.gpg dists/$OUT_REPO/Release

echo "performing rsync of repo $RELEASE_DIR/dist/$OUT_REPO to osm-download.etsi.org:/repos/"
cd $CURR_DIR/$REPO_BASE

# copy over the public key file
[ "$PUBLIC_KEY_FILE" ] && cp "$PUBLIC_KEY_FILE" osm/debian/$RELEASE_DIR

# copy over the changelog file
[ "$CHANGE_LOG_FILE" ] && cp "$CHANGE_LOG_FILE" osm/debian/$RELEASE_DIR

rsync -avR $RSYNC_OPTIONS osm/debian/$RELEASE_DIR rsync://$RSYNC_USER_HOST/repos

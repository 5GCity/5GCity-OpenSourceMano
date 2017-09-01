#
#   Copyright 2016 Telefónica Investigación y Desarrollo, S.A.U.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
#!/bin/sh

echo GERRIT BRANCH is $GERRIT_BRANCH
dpkg -l wget &>/dev/null ||sudo apt-get install -y wget
dpkg -l curl &>/dev/null ||sudo apt-get install -y curl
#Curl can be used instead of wget:
#curl -s -X POST -d @$file https://osm.etsi.org/fossology/?mod=agent_nomos_once

apache=0
nolicense=0
other=0

git fetch

RE="FATAL: your file did not get passed through"

for file in $(git diff --name-only origin/$GERRIT_BRANCH); do
    if [ -f $file ]; then
        if [ -s $file ]; then
            license=$(wget -qO - --post-file $file https://osm.etsi.org/fossology/?mod=agent_nomos_once |sed "s/^[ \t]*//;s/[ \t]*$//")
            result=$(echo $license | grep "$RE")
            if [ -n "$result" ]; then
                # possibly we have exceeded the post rate
                sleep 10
                license=$(wget -qO - --post-file $file https://osm.etsi.org/fossology/?mod=agent_nomos_once |sed "s/^[ \t]*//;s/[ \t]*$//")
            fi
        else
            license="No_license_found"
        fi
    else
        license="DELETED"
    fi
    echo "$file $license"
    case "$license" in
        "Apache-2.0")
            apache=$((apache + 1))
            ;;
        "No_license_found")
            nolicense=$((nolicense + 1))
            ;;
        "DELETED")
            ;;
        "FATAL:*")
            ;;
        *)
            echo "BAD LICENSE ON FILE $file"
            other=$((other + 1))
            ;;
    esac
done

if [ $other -gt 0 ]; then
    echo "FATAL: Non-apache licenses detected"
    exit 2
fi

if [ $nolicense -gt 0 ]; then
    echo "WARNING: Unlicensed files found"
fi

exit 0

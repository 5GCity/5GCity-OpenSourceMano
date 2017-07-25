#!/usr/bin/env python
#
#   Copyright 2017 Sandvine
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
#
import requests
import json
import pprint
import argparse

parser=argparse.ArgumentParser(description="Tool to retrieve the latest build from the artifactory server")
parser.add_argument('branch')
parser.add_argument('--project',default='osm-stage_3')
parser.add_argument('--url',default='http://osm1.etsi.org:8081/artifactory/api/build/')
args = parser.parse_args()

url = args.url + args.project + " :: " + args.branch

resp = requests.get(url)
jsonData = json.loads(resp.content)

if 'buildsNumbers' not in jsonData:
    print("Cannot find any valid builds")
    exit(1)

# first entry is the latest build
build = sorted(jsonData['buildsNumbers'], key=lambda x: int(x['uri'][1:]),reverse=True)[0]

print "{} :: {}{}".format(args.project,args.branch,build['uri'])

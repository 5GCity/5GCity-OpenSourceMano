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

from dateutil import parser
from dateutil.tz import tzutc
from datetime import datetime
import time

arg_parser=argparse.ArgumentParser(description="Tool to retrieve the latest build from the artifactory server")
arg_parser.add_argument('--branch',default=None)
arg_parser.add_argument('repo')
arg_parser.add_argument('--url',default='http://osm1.etsi.org:8081/')
arg_parser.add_argument('--keep',default=5)
arg_parser.add_argument('--password',default='')
arg_parser.add_argument('--debug',default=None)

args = arg_parser.parse_args()


if args.branch:
    url = args.url + 'artifactory/api/storage/' + args.repo + '/' + args.branch
    delete_url = args.url + 'artifactory/' + args.repo + '/' + args.branch
else:
    url = args.url + 'artifactory/api/storage/' + args.repo
    delete_url = args.url + 'artifactory/' + args.repo

resp = requests.get(url)
jsonData = json.loads(resp.content)

# first entry is the latest build
filtered_list = filter(lambda x: x['uri'].split('/')[1].isdigit(), jsonData['children'])
folders_sorted = sorted(filtered_list, key=lambda x: int(x['uri'].split('/')[1]),reverse=True)

if len(folders_sorted) < int(args.keep):
    print("nothing to cleanup")
    exit(0)


for entry in folders_sorted[int(args.keep):]:
    if args.debug:
        print("going to delete {}".format(delete_url+entry['uri']))
    else:
        requests.delete(delete_url + entry['uri'], auth=('admin',args.password))


# empty the trash can
empty_trash_url=args.url + 'artifactory/ui/artifactactions/emptytrash'
headers = {'Content-Type': 'application/json'}
requests.post(empty_trash_url,headers=headers,auth=('admin',args.password))



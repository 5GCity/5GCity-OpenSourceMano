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
arg_parser.add_argument('branch')
arg_parser.add_argument('--project',default='osm-stage_3')
arg_parser.add_argument('--url',default='http://osm1.etsi.org:8081/')
arg_parser.add_argument('--keep',default=5)
arg_parser.add_argument('--password',default='')
args = arg_parser.parse_args()

url = args.url + 'artifactory/api/build/' + args.project + " :: " + args.branch

resp = requests.get(url)
jsonData = json.loads(resp.content)
if 'buildsNumbers' not in jsonData:
    print("Cannot find any valid builds")
    exit(1)

# first entry is the latest build
buildlist = sorted(jsonData['buildsNumbers'], key=lambda x: int(x['uri'][1:]),reverse=True)
print("total builds is {}".format(len(buildlist)))
pprint.pprint(buildlist)

if len(buildlist) < args.keep:
    print("nothing to cleanup")
    exit(0)

def convert_to_ms(datetime):
    #get the millisecond from the date/time
    ms=datetime.split('.')[1].split('+')[0]
    parser_out=parser.parse(datetime)
    timeval=parser_out
    tuple=int(time.mktime(timeval.timetuple()))
    return (tuple*1000+int(ms)-(time.timezone*1000))

def buildPost(dateInMS,buildNumber):
    build = {}
    data = {}
    build['buildName'] = args.project + " :: " + args.branch
    build['buildNumber'] = buildNumber
    build['date'] = str(dateInMS)

    data['buildsCoordinates'] = list()
    data['buildsCoordinates'].append(build)
    return data
    
delete_url = args.url + 'artifactory/ui/builds/buildsDelete'
headers = {'Content-Type': 'application/json'}

for entry in buildlist[int(args.keep):]:
   ms = convert_to_ms(entry['started'])
   buildNumber = entry['uri'].split('/')[1]
   print("deleting build {} ms {}".format(args.project + " :: " + args.branch + '/' + buildNumber,ms))
   postData = buildPost(ms,entry['uri'].split('/')[1])

   requests.post(delete_url,data=json.dumps(postData),headers=headers,auth=('admin',args.password))

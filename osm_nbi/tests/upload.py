#! /usr/bin/python3
# -*- coding: utf-8 -*-

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import getopt
import sys
import requests
from os.path import getsize, basename
from hashlib import md5

__author__ = "Alfonso Tierno, alfonso.tiernosepulveda@telefonica.com"
__date__ = "$2018-01-01$"
__version__ = "0.1"
version_date = "Jan 2018"


def usage():
    print("Usage: ", sys.argv[0], "[options]")
    print("      --version: prints current version")
    print("      -f|--file FILE: file to be sent")
    print("      -h|--help: shows this help")
    print("      -u|--url URL: complete server URL")
    print("      -s|--chunk-size SIZE: size of chunks, by default 1000")
    print("      -t|--token TOKEN: Authorizaton token, previously obtained from server")
    print("      -v|--verbose print debug information, can be used several times")
    return


if __name__ == "__main__":
    try:
        # load parameters and configuration
        opts, args = getopt.getopt(sys.argv[1:], "hvu:s:f:t:",
                                   ["url=", "help", "version", "verbose", "file=", "chunk-size=", "token="])
        url = None
        chunk_size = 500
        pkg_file = None
        verbose = 0
        token = None

        for o, a in opts:
            if o == "--version":
                print("upload version " + __version__ + ' ' + version_date)
                sys.exit()
            elif o in ("-v", "--verbose"):
                verbose += 1
            elif o in ("-h", "--help"):
                usage()
                sys.exit()
            elif o in ("-u", "--url"):
                url = a
            elif o in ("-s", "--chunk-size"):
                chunk_size = int(a)
            elif o in ("-f", "--file"):
                pkg_file = a
            elif o in ("-t", "--token"):
                token = a
            else:
                assert False, "Unhandled option"
        total_size = getsize(pkg_file)
        index = 0
        transaction_id = None
        file_md5 = md5()
        with open(pkg_file, 'rb') as f:
            headers = {
                "Content-type": "application/gzip",
                "Content-Filename": basename(pkg_file),
                "Accept": "application/json",
            }
            if token:
                headers["Authorization"] = token
            while index < total_size:
                chunk_data = f.read(chunk_size)
                file_md5.update(chunk_data)
                # payload = {"file_name": pkg_file, "chunk_data": base64.b64encode(chunk_data).decode("utf-8"),
                #            "chunk_size": chunk_size}
                if transaction_id:
                    headers["Transaction-Id"] = transaction_id
                if index+len(chunk_data) == total_size:
                    headers["Content-File-MD5"] = file_md5.hexdigest()
                #    payload["id"] = transaction_id
                headers["Content-range"] = "bytes {}-{}/{}".format(index, index+len(chunk_data)-1, total_size)
                # refers to rfc2616:  https://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html
                if verbose:
                    print("TX chunk Headers: {}".format(headers))
                r = requests.post(url, data=chunk_data, headers=headers, verify=False)
                if r.status_code not in (200, 201):
                    print("Got {}: {}".format(r.status_code, r.text))
                    exit(1)
                if verbose > 1:
                    print("RX {}: {}".format(r.status_code, r.text))
                response = r.json()
                if not transaction_id:
                    transaction_id = response["id"]
                index += len(chunk_data)
            if verbose <= 1:
                print("RX {}: {}".format(r.status_code, r.text))
            if "id" in response:
                print("---\nid: {}".format(response["id"]))
    except Exception:
        raise

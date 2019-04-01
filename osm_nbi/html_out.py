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

"""
Contains html text in variables to make and html response
"""

import yaml
from http import HTTPStatus
from html import escape as html_escape

__author__ = "Alfonso Tierno <alfonso.tiernosepulveda@telefonica.com>"

html_start = """
 <!DOCTYPE html>
<html>
<head>
  <link href="/osm/static/style.css" rel="stylesheet">
<title>Welcome to OSM</title>
</head>
<body>
  <div id="osm_topmenu">
    <div>
      <a href="https://osm.etsi.org"> <img src="/osm/static/OSM-logo.png" height="42" width="100"
        style="vertical-align:middle"> </a>
      <a>( {} )</a>
      <a href="/osm/pdu/v1/pdu_descriptors">PDUs </a>
      <a href="/osm/vnfpkgm/v1/vnf_packages">VNFDs </a>
      <a href="/osm/nsd/v1/ns_descriptors">NSDs </a>
      <a href="/osm/nslcm/v1/ns_instances">NSs </a>
      <a href="/osm/nst/v1/netslice_templates">NSTDs </a>
      <a href="/osm/nsilcm/v1/netslice_instances">NSIs </a>
      <a href="/osm/admin/v1/users">USERs </a>
      <a href="/osm/admin/v1/projects">PROJECTs </a>
      <a href="/osm/admin/v1/tokens">TOKENs </a>
      <a href="/osm/admin/v1/vim_accounts">VIMs </a>
      <a href="/osm/admin/v1/wim_accounts">WIMs </a>
      <a href="/osm/admin/v1/sdns">SDNs </a>
      <a href="/osm/admin/v1/tokens?METHOD=DELETE">logout </a>
    </div>
  </div>
"""

html_body = """
<h1>{item}</h1>
"""

html_end = """
</body>
</html>
"""

html_body_error = "<h2> Error <pre>{}</pre> </h2>"


html_auth2 = """
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
<html>
<head><META http-equiv="Content-Type" content="text/html; charset=UTF-8">
  <link href="/osm/static/style.css" rel="stylesheet">
  <title>OSM Login</title>
</head>
<body>
  <div id="osm_header">
    <div>
      <a href="https://osm.etsi.org"> <h1><img src="/osm/static/OSM-logo.png" style="vertical-align:middle"></h1> </a>
    </div>
  </div>
  <div id="osm_error_message">
    <h1>{error}</h1>
  </div>
  <div class="gerritBody" id="osm_body">
    <h1>Sign in to OSM</h1>
    <form action="/osm/admin/v1/tokens" id="login_form" method="POST">
      <table style="border: 0;">
        <tr><th>Username</th><td><input id="f_user" name="username" size="25" tabindex="1" type="text"></td></tr>
        <tr><th>Password</th><td><input id="f_pass" name="password" size="25" tabindex="2" type="password"></td></tr>
        <tr><td><input tabindex="3" type="submit" value="Sign In"></td></tr>
      </table>
    </form>
    <div style="clear: both; margin-top: 15px; padding-top: 2px; margin-bottom: 15px;">
      <div id="osm_footer">
        <div></div>
      </div>
    </div>
  </div>
  <script src="/osm/static/login.js"> </script>
</body>
</html>
"""

html_upload_body = """
<form action="/osm{}" method="post" enctype="multipart/form-data">
    <h3> <table style="border: 0;"> <tr>
        <td> Upload {} descriptor (tar.gz)  file: <input type="file" name="descriptor_file"/> </td>
        <td> <input type="submit" value="Upload"/> </td>
    </tr> </table> </h3>
</form>
"""

html_nslcmop_body = """
<a href="/osm/nslcm/v1/ns_lcm_op_occs?nsInstanceId={id}">nslcm operations </a>
<a href="/osm/nslcm/v1/vnf_instances?nsr-id-ref={id}">VNFRS </a>
<form action="/osm/nslcm/v1/ns_instances/{id}/terminate" method="post" enctype="multipart/form-data">
    <h3> <table style="border: 0;"> <tr>
        <td> <input type="submit" value="Terminate"/> </td>
    </tr> </table> </h3>
</form>
"""

html_nsilcmop_body = """
<a href="/osm/nsilcm/v1/nsi_lcm_op_occs?nsiInstanceId={id}">nsilcm operations </a>
<form action="/osm/nsilcm/v1/netslice_instances/{id}/terminate" method="post" enctype="multipart/form-data">
    <h3> <table style="border: 0;"> <tr>
        <td> <input type="submit" value="Terminate"/> </td>
    </tr> </table> </h3>
</form>
"""


def format(data, request, response, session):
    """
    Format a nice html response, depending on the data
    :param data:
    :param request: cherrypy request
    :param response: cherrypy response
    :return: string with teh html response
    """
    response.headers["Content-Type"] = 'text/html'
    if response.status == HTTPStatus.UNAUTHORIZED.value:
        if response.headers.get("WWW-Authenticate") and request.config.get("auth.allow_basic_authentication"):
            response.headers["WWW-Authenticate"] = "Basic" + response.headers["WWW-Authenticate"][6:]
            return
        else:
            return html_auth2.format(error=data)
    body = html_body.format(item=request.path_info)
    if response.status and response.status > 202:
        body += html_body_error.format(yaml.safe_dump(data, explicit_start=True, indent=4, default_flow_style=False))
    elif isinstance(data, (list, tuple)):
        if request.path_info == "/vnfpkgm/v1/vnf_packages":
            body += html_upload_body.format(request.path_info, "VNFD")
        elif request.path_info == "/nsd/v1/ns_descriptors":
            body += html_upload_body.format(request.path_info + "_content", "NSD")
        elif request.path_info == "/nst/v1/nst_templates":
            body += html_upload_body.format(request.path_info + "_content", "NSTD")
        for k in data:
            if isinstance(k, dict):
                data_id = k.pop("_id", None)
            elif isinstance(k, str):
                data_id = k
            body += '<p> <a href="/osm/{url}/{id}">{id}</a>: {t} </p>'.format(url=request.path_info, id=data_id,
                                                                              t=html_escape(str(k)))
    elif isinstance(data, dict):
        if "Location" in response.headers:
            body += '<a href="{}"> show </a>'.format(response.headers["Location"])
        else:
            body += '<a href="/osm/{}?METHOD=DELETE"> <img src="/osm/static/delete.png" height="25" width="25"> </a>'\
                .format(request.path_info)
            if request.path_info.startswith("/nslcm/v1/ns_instances_content/") or \
                    request.path_info.startswith("/nslcm/v1/ns_instances/"):
                _id = request.path_info[request.path_info.rfind("/")+1:]
                body += html_nslcmop_body.format(id=_id)
            elif request.path_info.startswith("/nsilcm/v1/netslice_instances_content/") or \
                    request.path_info.startswith("/nsilcm/v1/netslice_instances/"):
                _id = request.path_info[request.path_info.rfind("/")+1:]
                body += html_nsilcmop_body.format(id=_id)
        body += "<pre>" + html_escape(yaml.safe_dump(data, explicit_start=True, indent=4, default_flow_style=False)) + \
                "</pre>"
    elif data is None:
        if request.method == "DELETE" or "METHOD=DELETE" in request.query_string:
            body += "<pre> deleted </pre>"
    else:
        body = html_escape(str(data))
    user_text = "    "
    if session:
        if session.get("username"):
            user_text += "user: {}".format(session.get("username"))
        if session.get("project_id"):
            user_text += ", project: {}".format(session.get("project_id"))
    return html_start.format(user_text) + body + html_end
    # yaml.safe_dump(data, explicit_start=True, indent=4, default_flow_style=False)
    # tags=False,
    # encoding='utf-8', allow_unicode=True)

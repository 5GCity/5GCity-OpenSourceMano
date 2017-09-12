/* Copyright 2017 Sandvine
 *
 * All Rights Reserved.
 * 
 *   Licensed under the Apache License, Version 2.0 (the "License"); you may
 *   not use this file except in compliance with the License. You may obtain
 *   a copy of the License at
 *
 *        http://www.apache.org/licenses/LICENSE-2.0
 *
 *   Unless required by applicable law or agreed to in writing, software
 *   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 *   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 *   License for the specific language governing permissions and limitations
 *   under the License.
 */

def get_archive(artifactory_server, mdg, branch, build_name, build_number, pattern='*') {
    server = Artifactory.server artifactory_server

    println("retrieve archive for ${mdg}/${branch}/${build_name}/${build_number}/${pattern}")

    def repo_prefix = 'osm-'
    def downloadSpec = """{
     "files": [
        {
          "target": "./",
          "pattern": "${repo_prefix}${mdg}/${branch}/${pattern}",
          "build": "${build_name}/${build_number}"
        }
     ]
    }"""

    server.download(downloadSpec)
    // workaround.  flatten and repo the specific build num from the directory
    sh "cp -R ${build_num}/* ."
    sh "rm -rf ${build_num}"
}

def get_env_value(build_env_file,key) {
    return sh(returnStdout:true,  script: "cat ${build_env_file} | awk -F= '/${key}/{print \$2}'").trim()
}

def lxc_run(container_name,cmd) {
    return sh(returnStdout: true, script: "lxc exec ${container_name} -- ${cmd}").trim()
}

// start a http server
// return the http server URL
def start_http_server(repo_dir,server_name) {
    sh "docker run -dit --name ${server_name} -v ${repo_dir}:/usr/local/apache2/htdocs/ httpd:2.4"
    def http_server_ip = sh(returnStdout:true,  script: "docker inspect --format '{{ .NetworkSettings.IPAddress }}' ${server_name}").trim()
    return "-u http://${http_server_ip}/"
}

def lxc_get_file(container_name,file,destination) {
    sh "lxc file pull ${container_name}/${file} ${destination}"
}

def systest_run(container_name, test) {
    // need to get the SO IP inside the running container
    so_ip = lxc_run(container_name,"lxc list SO-ub -c 4|grep eth0 |awk '{print \$2}'")
    //container_ip = get_ip_from_container(container_name)
    // 
    lxc_run(container_name, "make -C devops/systest OSM_HOSTNAME=${so_ip} ${test}")
    lxc_get_file(container_name, "/root/devops/systest/reports/pytest-${test}.xml",'.')
}

def get_ip_from_container( container_name ) {
    return sh(returnStdout: true, script: "lxc list ${container_name} -c 4|grep eth0 |awk '{print \$2}'").trim()
}

def archive(artifactory_server,mdg,branch,status) {
    server = Artifactory.server artifactory_server

    def properties = "branch=${branch};status=${status}"
    def repo_prefix = 'osm-'
    def uploadSpec = """{
     "files": [
        {
          "pattern": "dists/*.gz",
          "target": "${repo_prefix}${mdg}/${branch}/${BUILD_NUMBER}/",
          "props": "${properties}",
          "flat": false
        },
        {
          "pattern": "dists/*Packages",
          "target": "${repo_prefix}${mdg}/${branch}/${BUILD_NUMBER}/",
          "props": "${properties}",
          "flat": false
        },
        {
          "pattern": "pool/*/*.deb",
          "target": "${repo_prefix}${mdg}/${branch}/${BUILD_NUMBER}/",
          "props": "${properties}",
          "flat": false
        }]
    }"""

    buildInfo = server.upload(uploadSpec)
    //buildInfo.retention maxBuilds: 4
    //buildInfo.retention deleteBuildArtifacts: false

    server.publishBuildInfo(buildInfo)

    // store the build environment into the jenkins artifact storage
    sh 'env > build.env'
    archiveArtifacts artifacts: "build.env", fingerprint: true
}


//CANNOT use build promotion with OSS version of artifactory
// For now, will publish downloaded artifacts into a new repo.
def promote_build(artifactory_server,mdg,branch,buildInfo) {
    println("Promoting build: mdg: ${mdg} branch: ${branch} build: ${buildInfo.name}/${buildInfo.number}")

    server = Artifactory.server artifactory_server

    //def properties = "branch=${branch};status=${status}"
    def repo_prefix = 'osm-'
    def build_name = "${mdg}-stage_2 :: ${branch}"

    def promotionConfig = [
        // Mandatory parameters
        "buildName"          : buildInfo.name,
        "buildNumber"        : buildInfo.number,
        'targetRepo'         : 'osm-release',
     
        // Optional parameters
        'comment'            : 'this is the promotion comment',
        'sourceRepo'         : "${repo_prefix}${mdg}",
        'status'             : 'Testing',
        'includeDependencies': true,
        'copy'               : true,
        // 'failFast' is true by default.
        // Set it to false, if you don't want the promotion to abort upon receiving the first error.
        'failFast'           : true
    ]

    server.promote promotionConfig
}

def get_mdg_from_project(project) {
    // split the project.
    def values = project.split('/')
    if ( values.size() > 1 ) {
        return values[1]
    }
    // no prefix, likely just the project name then
    return project
}


return this

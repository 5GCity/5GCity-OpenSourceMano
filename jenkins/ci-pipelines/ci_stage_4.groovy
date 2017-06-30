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

properties([
    parameters([
        string(defaultValue: 'osm-stage_3', description: '', name: 'UPSTREAM_PROJECT'),
        string(defaultValue: 'release', description: '', name: 'RELEASE'),
        string(defaultValue: 'pipeline', description: '', name: 'NODE'),
    ])
])

node("${params.NODE}") {

    stage("checkout") {
        checkout scm
    }

    ci_helper = load "jenkins/ci-pipelines/ci_helper.groovy"

    stage("get artifacts") {
        // grab the upstream artifact name
        step ([$class: 'CopyArtifact',
              projectName: "${params.UPSTREAM_PROJECT}/${BRANCH_NAME}"])
    }

    container_name = sh(returnStdout: true, script: 'cat build_version.txt').trim()

    stage("Test") {
        ci_helper.systest_run(container_name, 'smoke')
        junit '*.xml'
    }

/*  os_credentials = "OS_AUTH_URL=${params.OS_AUTH_URL} OS_USERNAME=${params.OS_USERNAME} OS_PASSWORD=${params.OS_PASSWORD} OS_PROJECT_NAME=${params.OS_PROJECT_NAME}"
        stage("cirros-test") {
            sh """
               make -C systest OSM_HOSTNAME=${osm_ip} ${os_credentials} cirros
               """
            junit 'systest/reports/pytest-cirros.xml'
        }
*/
}

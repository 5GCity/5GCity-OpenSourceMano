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
        string(defaultValue: '', description: '', name: 'CONTAINER_NAME' ),
        string(defaultValue: 'osm-stage_3', description: '', name: 'UPSTREAM_PROJECT'),
        string(defaultValue: 'pipeline', description: '', name: 'NODE'),
        string(defaultValue: '/home/jenkins/hive/openstack-telefonica.rc', description: '', name: 'HIVE_VIM_1'),
    ])
])

node("${params.NODE}") {

    stage("checkout") {
        checkout scm
    }

    ci_helper = load "jenkins/ci-pipelines/ci_helper.groovy"

    if ( params.CONTAINER_NAME ) {
        container_name = params.CONTAINER_NAME
    }
    else if ( params.UPSTREAM_PROJECT ) {
        step ([$class: 'CopyArtifact',
              projectName: "${params.UPSTREAM_PROJECT}/${BRANCH_NAME}"])
        container_name = sh(returnStdout: true, script: 'cat build_version.txt').trim()
    }
    else {
        println("no OSM container found")
        currentBuild.result = 'FAILURE'
        return
    }
    println("OSM container = ${container_name}")

    if ( params.HIVE_VIM_1 ) {
        stage( "${params.HIVE_VIM_1}" ) {
            ci_helper.systest_run(container_name, 'cirros', params.HIVE_VIM_1)
            ci_helper.systest_run(container_name, 'ns_scale', params.HIVE_VIM_1)
            junit '*.xml'
        }
    }
}

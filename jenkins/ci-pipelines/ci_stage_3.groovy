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
        string(defaultValue: env.GERRIT_BRANCH, description: '', name: 'GERRIT_BRANCH'),
        string(defaultValue: 'system', description: '', name: 'NODE'),
        string(defaultValue: '', description: '', name: 'BUILD_FROM_SOURCE'),
        string(defaultValue: 'unstable', description: '', name: 'REPO_DISTRO'),
        string(defaultValue: '', description: '', name: 'COMMIT_ID'),
        string(defaultValue: '-stage_2', description: '', name: 'UPSTREAM_SUFFIX'),
        string(defaultValue: 'pubkey.asc', description: '', name: 'REPO_KEY_NAME'),
        string(defaultValue: 'release', description: '', name: 'RELEASE'),
        string(defaultValue: '', description: '', name: 'UPSTREAM_JOB_NAME'),
        string(defaultValue: '', description: '', name: 'UPSTREAM_JOB_NUMBER'),
        string(defaultValue: '', description: '', name: 'UPSTREAM_JOB_NUMBER'),
        string(defaultValue: 'dpkg1', description: '', name: 'GPG_KEY_NAME'),
        booleanParam(defaultValue: false, description: '', name: 'SAVE_CONTAINER_ON_FAIL'),
        booleanParam(defaultValue: false, description: '', name: 'SAVE_CONTAINER_ON_PASS'),
    ])
])

node("${params.NODE}") {

    sh 'env'

    tag_or_branch = params.GERRIT_BRANCH.replaceAll(/\./,"")
    container_name_prefix = "osm-${tag_or_branch}" 
    container_name = "${container_name_prefix}-${BUILD_NUMBER}"

    stage("Checkout") {
        checkout scm
    }

    ci_helper = load "jenkins/ci-pipelines/ci_helper.groovy"

    // Copy the artifacts from the upstream jobs
    stage("Copy Artifacts") {
        // cleanup any previous repo
        sh 'rm -rf repo'
        if ( params.UPSTREAM_SUFFIX ) {

            dir("repo") {
                // grab all stable upstream builds based on the
                // given target UPSTREAM_SUFFIX

                dir("${RELEASE}") {
                    def list = ["SO", "UI", "RO", "openvim", "osmclient"]
                    for (component in list) {
                        step ([$class: 'CopyArtifact',
                               projectName: "${component}${params.UPSTREAM_SUFFIX}/${GERRIT_BRANCH}"])

                        // grab the build name/number
                        //options = get_env_from_build('build.env')
                        build_num = ci_helper.get_env_value('build.env','BUILD_NUMBER')
                        //build_num = sh(returnStdout:true,  script: "cat build.env | awk -F= '/BUILD_NUMBER/{print \$2}'").trim()
                        ci_helper.get_archive(component,GERRIT_BRANCH, "${component}-stage_2 :: ${GERRIT_BRANCH}", build_num)

                        // cleanup any prevously defined dists
                        sh "rm -rf dists"
                    }

                    // check if an upstream artifact based on specific build number has been requested
                    // This is the case of a merge build and the upstream merge build is not yet complete (it is not deemed
                    // a successful build yet). The upstream job is calling this downstream job (with the its build artifiact)
                    if ( params.UPSTREAM_JOB_NAME ) {
                        step ([$class: 'CopyArtifact',
                               projectName: "${params.UPSTREAM_JOB_NAME}",
                               selector: [$class: 'SpecificBuildSelector', buildNumber: "${params.UPSTREAM_JOB_NUMBER}"]
                              ])

                        //options = get_env_from_build('build.env')
                        // grab the build name/number
                        //build_num = sh(returnStdout:true,  script: "cat build.env | awk -F= '/BUILD_NUMBER/{print \$2}'").trim()
                        build_num = ci_helper.get_env_value('build.env','BUILD_NUMBER')
                        component = ci_helper.get_mdg_from_project(ci_helper.get_env_value('build.env','GERRIT_PROJECT'))

                        ci_helper.get_archive(component,GERRIT_BRANCH, "${component}-stage_2 :: ${GERRIT_BRANCH}", build_num)

                        sh "rm -rf dists"
                    }
                    
                    // sign all the components
                    for (component in list) {
                        sh "dpkg-sig --sign builder -k ${GPG_KEY_NAME} pool/${component}/*"
                    }

                    // now create the distro
                    for (component in list) {
                        sh "mkdir -p dists/${params.REPO_DISTRO}/${component}/binary-amd64/"
                        sh "apt-ftparchive packages pool/${component} > dists/${params.REPO_DISTRO}/${component}/binary-amd64/Packages"
                        sh "gzip -9fk dists/${params.REPO_DISTRO}/${component}/binary-amd64/Packages"
                    }

                    // create and sign the release file
                    sh "apt-ftparchive release dists/${params.REPO_DISTRO} > dists/${params.REPO_DISTRO}/Release"
                    sh "gpg --yes -abs -u ${GPG_KEY_NAME} -o dists/${params.REPO_DISTRO}/Release.gpg dists/${params.REPO_DISTRO}/Release"

                    // copy the public key into the release folder
                    // this pulls the key from the home dir of the current user (jenkins)
                    sh "cp ~/${REPO_KEY_NAME} ."
                }
                // start an apache server to serve up the images
                http_server_name = "${container_name}-apache"

                pwd = sh(returnStdout:true,  script: 'pwd').trim()
                repo_base_url = ci_helper.start_http_server(pwd,http_server_name)
            }
        }
    }

    error = null

    try {
        stage("Install") {

            //will by default always delete containers on complete
            //sh "jenkins/system/delete_old_containers.sh ${container_name_prefix}"

            commit_id = ''
            repo_distro = ''
            repo_key_name = ''
            release = ''

            if ( params.COMMIT_ID )
            {
                commit_id = "-b ${params.COMMIT_ID}"
            }

            if ( params.REPO_DISTRO )
            {
                repo_distro = "-r ${params.REPO_DISTRO}"
            }

            if ( params.REPO_KEY_NAME )
            {
                repo_key_name = "-k ${params.REPO_KEY_NAME}"
            }

            if ( params.RELEASE )
            {
                release = "-R ${params.RELEASE}"
            }
     
            sh """
                export OSM_USE_LOCAL_DEVOPS=true
                jenkins/host/start_build system --build-container ${container_name} \
                                                ${commit_id} \
                                                ${repo_distro} \
                                                ${repo_base_url} \
                                                ${repo_key_name} \
                                                ${release} \
                                                ${params.BUILD_FROM_SOURCE}
               """
        }

        stage("Test") {
            ci_helper.systest_run(container_name, 'smoke')
            junit '*.xml'
        }

        stage("Archive") {
            sh "echo ${container_name} > build_version.txt"
            archiveArtifacts artifacts: "build_version.txt", fingerprint: true

            // Archive the tested repo
            dir("repo/${RELEASE}") {
                ci_helper.archive(RELEASE,GERRIT_BRANCH,'tested')
            }
        }
    }
    catch(caughtError) {
        error = caughtError
        currentBuild.result = 'FAILURE'
    }
    finally {
        sh "docker stop ${http_server_name}"

        if (error) {
            if ( !params.SAVE_CONTAINER_ON_FAIL ) {
                sh "lxc delete ${container_name} --force"
            }
            throw error 
        }
        else {
            if ( !params.SAVE_CONTAINER_ON_PASS ) {
                sh "lxc delete ${container_name} --force"
            }
        }
    }
}

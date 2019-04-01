/*
  Licensed under the Apache License, Version 2.0 (the "License");
  you may not use this file except in compliance with the License.
  You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
  implied.
  See the License for the specific language governing permissions and
  limitations under the License.
*/
properties([
    parameters([
        string(defaultValue: env.BRANCH_NAME, description: '', name: 'GERRIT_BRANCH'),
        string(defaultValue: 'osm/NBI', description: '', name: 'GERRIT_PROJECT'),
        string(defaultValue: env.GERRIT_REFSPEC, description: '', name: 'GERRIT_REFSPEC'),
        string(defaultValue: env.GERRIT_PATCHSET_REVISION, description: '', name: 'GERRIT_PATCHSET_REVISION'),
        string(defaultValue: 'https://osm.etsi.org/gerrit', description: '', name: 'PROJECT_URL_PREFIX'),
        booleanParam(defaultValue: false, description: '', name: 'TEST_INSTALL'),
        string(defaultValue: 'artifactory-osm', description: '', name: 'ARTIFACTORY_SERVER'),
    ])
])

def devops_checkout() {
    dir('devops') {
        git url: "${PROJECT_URL_PREFIX}/osm/devops", branch: params.GERRIT_BRANCH
    }
}

node('docker') {
    checkout scm
    devops_checkout()

    ci_stage_2 = load "devops/jenkins/ci-pipelines/ci_stage_2.groovy"
    ci_stage_2.ci_pipeline( 'NBI',
                           params.PROJECT_URL_PREFIX,
                           params.GERRIT_PROJECT,
                           params.GERRIT_BRANCH,
                           params.GERRIT_REFSPEC,
                           params.GERRIT_PATCHSET_REVISION,
                           params.TEST_INSTALL,
                           params.ARTIFACTORY_SERVER)
}

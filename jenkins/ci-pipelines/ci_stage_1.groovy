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

def Get_MDG(project) {
    // split the project.
    def values = project.split('/')
    if ( values.size() > 1 ) {
        return values[1]
    }
    // no prefix, likely just the project name then
    return project
}

node("${params.NODE}") {

    mdg = Get_MDG("${GERRIT_PROJECT}")
    println("MDG is ${mdg}")

    if ( params.PROJECT_URL_PREFIX == null )
    {
        params.PROJECT_URL_PREFIX  = 'https://osm.etsi.org/gerrit'
    }

    stage('downstream') {
        // initially use stage_name as the event_type
        def stage_name = GERRIT_EVENT_TYPE

        switch(GERRIT_EVENT_TYPE) {
            case "change-merged":
               stage_name = "stage_2-merge"
               break

            case "patchset-created":
               stage_name = "stage_2"
               break
        }

        // pipeline running from gerrit trigger.
        // kickoff the downstream multibranch pipeline
        def downstream_params = [
            string(name: 'GERRIT_BRANCH', value: GERRIT_BRANCH),
            string(name: 'GERRIT_PROJECT', value: GERRIT_PROJECT),
            string(name: 'GERRIT_REFSPEC', value: GERRIT_REFSPEC),
            string(name: 'GERRIT_PATCHSET_REVISION', value: GERRIT_PATCHSET_REVISION),
            string(name: 'PROJECT_URL_PREFIX', value: params.PROJECT_URL_PREFIX),
            booleanParam(name: 'TEST_INSTALL', value: params.TEST_INSTALL),
        ]
     
        if ( params.STAGE )
        {
            // go directly to stage 3 (osm system)
            stage_name = "stage_3"
            mdg = "osm"
            if ( ! params.TEST_INSTALL )
            {
                println("disabling stage_3 invocation")
                return
            }
        }
        // callout to stage_2.  This is a multi-branch pipeline.
        downstream_job_name = "${mdg}-${stage_name}/${GERRIT_BRANCH}"

        println("TEST_INSTALL = ${params.TEST_INSTALL}, downstream job: ${downstream_job_name}")

        stage_2_result = build job: "${downstream_job_name}", parameters: downstream_params, propagate: true
        if (stage_2_result.getResult() != 'SUCCESS') {
            project = stage_2_result.getProjectName()
            build = stage_2_result.getNumber()
            error("${project} build ${build} failed")
        }
    }
}

pipeline {
    agent {
        dockerfile true
    }
    stages {
        stage("Checkout") {
            steps {
                checkout scm
            }
        }
        stage("Test") {
            steps {
                sh 'make -j4 test'
            }
        }
        stage("Build") {
            steps {
                sh 'make package'
                stash name: "deb-files", includes: "deb_dist/*.deb"
            }
        }
        stage("Repo Component") {
            steps {
                unstash "deb-files"
                sh '''
                    mkdir -p pool/osmclient
                    mv deb_dist/*.deb pool/osmclient/
                    mkdir -p dists/unstable/osmclient/binary-amd64/
                    apt-ftparchive packages pool/osmclient > dists/unstable/osmclient/binary-amd64/Packages
                    gzip -9fk dists/unstable/osmclient/binary-amd64/Packages
                    '''
                archiveArtifacts artifacts: "dists/**,pool/osmclient/*.deb"
            }
        }
    }
}

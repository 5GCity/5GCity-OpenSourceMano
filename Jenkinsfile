pipeline {
    agent {
        dockerfile {
            label 'osm3'
        }
    }
    stages {
        stage("Checkout") {
            steps {
                checkout scm
                sh '''
                   groupadd -o -g $(id -g) -r jenkins
                   useradd -o -u $(id -u) --create-home -r -g  jenkins jenkins
                   '''
            }
        }
        stage("Test") {
            steps {
                sh 'tox'
            }
        }
        stage("Build") {
            steps {
                sh 'tox -e build'
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

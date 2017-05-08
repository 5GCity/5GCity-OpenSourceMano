node {
    stage("Checkout") {
        checkout scm
    }
    stage("Test") {
        sh 'make test'
    }
    stage("Build") {
        sh 'make package'
        stash name: "deb-files", includes: "deb_dist/*.deb"
    }
    stage("Repo Component") {
        releaseDir = "ReleaseTWO"
        unstash "deb-files"
        sh '''
            mkdir -p pool/osmclient
            mv deb_dist/*.deb pool/osmclient/
            mkdir -p dists/${releaseDir}/unstable/osmclient/binary-amd64/
            apt-ftparchive packages pool/osmclient > dists/${releaseDir}/unstable/osmclient/binary-amd64/Packages
            gzip -9fk dists/${releaseDir}/unstable/osmclient/binary-amd64/Packages
            '''
        archiveArtifacts artifacts: "dists/**,pool/osmclient/*.deb"
    }
}

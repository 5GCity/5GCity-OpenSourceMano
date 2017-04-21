pipeline {
	agent {
		label "pipeline"
	}
	stages {
		stage("Build") {
			agent {
				dockerfile true
			}
			steps {
				sh 'make package'
				stash name: "deb-files", includes: ".build/*.deb"
			}
		}
		stage("Unittest") {
			agent {
				dockerfile true
			}
			steps {
				sh 'echo "UNITTEST"'
			}
		}
		stage("Repo Component") {
			steps {
				unstash "deb-files"
				sh '''
					mkdir -p pool/RO
					mv .build/*.deb pool/RO/
					mkdir -p dists/$RELEASE/unstable/RO/binary-amd64/
					apt-ftparchive packages pool/RO > dists/$RELEASE/unstable/RO/binary-amd64/Packages
					gzip -9fk dists/$RELEASE/unstable/RO/binary-amd64/Packages
					'''
				archiveArtifacts artifacts: "dists/**,pool/RO/*.deb"
			}
		}
	}
}

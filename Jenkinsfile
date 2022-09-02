#!/usr/bin/env groovy

pipeline {

    agent {
        // Use the docker to assign the Python version.
        // Use the label to assign the node to run the test.
        // It is recommended by SQUARE team do not add the label.
        docker {
            image 'lsstts/develop-env:develop'
            args "-u root --entrypoint=''"
        }
    }

    options {
      disableConcurrentBuilds()
    }

    triggers {
        pollSCM('H * * * *')
    }

    environment {
        // SAL user home
        SAL_USERS_HOME = "/home/saluser"
        // SAL setup file
        SAL_SETUP_FILE = "/home/saluser/.setup.sh"
        // XML report path
        XML_REPORT = "jenkinsReport/report.xml"
        // Module name used in the pytest coverage analysis
        MODULE_NAME = "lsst.ts.authorize"
        // Target branch - either develop or master, depending on where we are
        // merging or what branch is run
        BRANCH = getBranchName(env.CHANGE_TARGET, env.BRANCH_NAME)
        // Authority to publish the document online
        user_ci = credentials('lsst-io')
        LTD_USERNAME = "${user_ci_USR}"
        LTD_PASSWORD = "${user_ci_PSW}"
        DOCUMENT_NAME = "ts-authorize"
        WORK_BRANCHES = "${GIT_BRANCH} ${CHANGE_BRANCH} develop"
    }

    stages {

        stage("Install Requirements And Update Branches") {
            steps {
                withEnv(["WHOME=${env.WORKSPACE}"]) {
                    sh """
                        source ${env.SAL_SETUP_FILE}
                        cd ${env.SAL_USERS_HOME}/repos/ts_config_ocs
                        ${env.SAL_USERS_HOME}/.checkout_repo.sh \${WORK_BRANCHES}
                        git pull
                        cd ${env.SAL_USERS_HOME}/repos/ts_xml
                        ${env.SAL_USERS_HOME}/.checkout_repo.sh \${WORK_BRANCHES}
                        git pull
                        cd ${env.SAL_USERS_HOME}/repos/ts_idl
                        ${env.SAL_USERS_HOME}/.checkout_repo.sh \${WORK_BRANCHES}
                        git pull
                        cd ${env.SAL_USERS_HOME}/repos/ts_salobj
                        ${env.SAL_USERS_HOME}/.checkout_repo.sh \${WORK_BRANCHES}
                        git pull
                        make_idl_files.py Authorize Script Test
                    """
                }
            }
        }

        stage ('Unit Tests and Coverage Analysis') {
            steps {
                // Pytest needs to export the junit report.
                withEnv(["WHOME=${env.WORKSPACE}"]) {
                    sh """
                        source ${env.SAL_SETUP_FILE}
                        setup -k -r .
                        pytest --cov-report html --cov=${env.MODULE_NAME} --junitxml=${env.WORKSPACE}/${env.XML_REPORT}
                    """
                }
            }
        }

        stage ('Build and Upload Documentation') {
            steps {
                withEnv(["WHOME=${env.WORKSPACE}"]) {
                    sh """
                        source ${env.SAL_SETUP_FILE}

                        setup -k -r .
                        package-docs build
                        ltd upload --product ${env.DOCUMENT_NAME} --git-ref ${BRANCH} --dir doc/_build/html
                    """
                }
            }
        }

    }

    post {
        always {
            // Change the ownership of workspace to Jenkins for the clean up
            // This is to work around the condition that the user ID of jenkins
            // is 1003 on TSSW Jenkins instance. In this post stage, it is the
            // jenkins to do the following clean up instead of the root in the
            // docker container.
            withEnv(["WHOME=${env.WORKSPACE}"]) {
                sh 'chown -R 1003:1003 ${HOME}/'
            }

            // The path of xml needed by JUnit is relative to
            // the workspace.
            junit "${env.XML_REPORT}"

            // Publish the HTML report
            publishHTML (target: [
                allowMissing: false,
                alwaysLinkToLastBuild: false,
                keepAll: true,
                reportDir: 'htmlcov',
                reportFiles: 'index.html',
                reportName: "Coverage Report"
            ])
        }
        regression {
            script {
                slackSend(color: "danger", message: "<@U72CH91L2> ${JOB_NAME} has suffered a regression ${BUILD_URL}", channel: "#jenkins-builds")
            }

        }
        fixed {
            script {
                slackSend(color: "good", message: "<@U72CH91L2> ${JOB_NAME} has been fixed ${BUILD_URL}", channel: "#jenkins-builds")
            }
        }
        cleanup {
            // clean up the workspace
            deleteDir()
        }
    }
}

// Return branch name. If changeTarget isn't defined, use branchName. Returns
// either develop or master
def getBranchName(changeTarget, branchName) {
    def branch = (changeTarget != null) ? changeTarget : branchName
    // If not master or develop, it's ticket branch and so the main branch is
    // develop. Can be adjusted with hotfix branches merging into master
    // if (branch.startsWith("hotfix")) { return "master" }
    // The reason to use the 'switch' instead of 'if' loop is to prepare for
    // future with more branches
    switch (branch) {
        case "master":
        case "develop":
            return branch
    }
    print("!!! Returning default for branch " + branch + " !!!\n")
    return "develop"
}

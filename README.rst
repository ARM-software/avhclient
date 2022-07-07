|build-badge| |test-badge| |cov-badge| |python-badge|
|wheel-badge| |pypi-badge| |license-badge|

.. |build-badge| image:: https://img.shields.io/github/workflow/status/ARM-software/avhclient/Build/main?style=flat
    :target: https://github.com/ARM-software/avhclient/actions/workflows/build.yml?query=event%3Apush+branch%3Amain+is%3Acompleted
    :alt: GitHub main-branch Build Workflow Status
.. |test-badge| image:: https://img.shields.io/testspace/tests/ARM-software/ARM-software:avhclient/main?compact_message
    :target: https://ARM-software.testspace.com/spaces/156681
    :alt: Unit tests results
.. |cov-badge| image:: https://img.shields.io/codecov/c/github/ARM-software/avhclient?style=flat
    :target: https://app.codecov.io/gh/ARM-software/avhclient/branch/main
    :alt: Codecov coverage report
.. |python-badge| image:: https://img.shields.io/pypi/pyversions/arm-avhclient?style=flat
    :target: https://pypi.org/project/arm-avhclient/
    :alt: PyPI - Python Version
.. |wheel-badge| image:: https://img.shields.io/pypi/wheel/arm-avhclient?style=flat
    :target: https://pypi.org/project/arm-avhclient/
    :alt: PyPI - Wheel
.. |pypi-badge| image:: https://img.shields.io/pypi/v/arm-avhclient?style=flat
    :target: https://pypi.org/project/arm-avhclient/
    :alt: PyPI
.. |license-badge| image:: https://img.shields.io/pypi/l/arm-avhclient?style=flat
    :target: https://pypi.org/project/arm-avhclient/
    :alt: PyPI - License

Arm Virtual Hardware Client (avhclient)
=======================================

The **Arm Virtual Hardware Client** (avhclient) is a python module that provides an interface for deploying and using  `Arm Virtual Hardware (AVH) <https://www.arm.com/products/development-tools/simulation/virtual-hardware>`_.

It enables uniform implementation of CI operations in various environments with reference examples provided for the following use cases:

* Jenkins CI pipelines
* GitHub-Actions workflows
* Local use with AVH targets

Other environments can be supported using demonstrated concepts as well.

**Example projects using AVH Client**

* `AVH-GetStarted <https://github.com/ARM-software/AVH-GetStarted>`_
* `CMSIS-RTOS2-Validation <https://github.com/ARM-software/CMSIS-RTOS2_Validation>`_
* `TensorFlow Lite for Microcontrollers <https://github.com/tensorflow/tflite-micro>`_

****

Installation
------------

Local installation
##################

Installing (development snapshot) directly from GitHub `main` branch::

    pip install git+https://github.com/ARM-software/avhclient.git@main
    
Docker container
################

Instead of installing Python and the AVH Client module into the local environment one
can use pre-built Docker images::

   docker pull ghcr.io/arm-software/avhclient

****

Backend Setup
-------------
avhclient can control different backends with Arm Virtual Hardware. Following options are currently available:

* ``aws`` (default) - interacts with AVH AMI available through `AWS Marketplace <https://arm-software.github.io/AVH/main/infrastructure/html/index.html#AWS>`_
* ``local`` - operates with AVH Targets installed locally.

The backend can be specified with ``-b`` option preceding the actual avhclient command.

Depending on the backend certain environment setup is expected.

AWS Backend Setup
#################

avhclient accesses AWS services via `Boto3 AWS SDK <https://github.com/boto/boto3>`_ and for that requires a set of parameters to be available in the environment.

AWS Credentials
***************
It is necessary to expose avhclient with the AWS credentials for your account.
You can either `export` your AWS credentials::

    export AWS_ACCESS_KEY_ID="YOUR_AWS_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="YOUR_AWS_SECRET_ACCESS_KEY"
    export AWS_SESSION_TOKEN="YOUR_AWS_SESSION_TOKEN"

or create a AWS credential file on `~/.aws/credentials (Linux & Mac)` or `%USERPROFILE%\.aws\credentials (Windows)`::

    [default]
    aws_access_key_id=YOUR_AWS_ACCESS_KEY_ID
    aws_secret_access_key=YOUR_AWS_SECRET_ACCESS_KEY
    aws_session_token=YOUR_AWS_SESSION_TOKEN

More info `AWS CLI config and credentials <https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html>`_

AWS Account info
****************
In order for avhclient to create or access an AVH instance following parameters need to be defined in the execution environment of avhclient:

* When creating and running a **new AVH instance**:
    Mandatory info::

        export AWS_IAM_PROFILE='YOUR_IAM_PROFILE'
        export AWS_SECURITY_GROUP_ID='YOUR_AWS_SECURITY_GROUP_ID'
        export AWS_SUBNET_ID='YOUR_SECURITY_GROUP_ID'
        export AWS_S3_BUCKET_NAME='YOUR_B3_BUCKET_NAME'

    Optional info (examples)::

        export AWS_AMI_ID=DESIRED_AVH_AMI_ID
        export AWS_AMI_VERSION=1.1.2
        export AWS_EFS_DNS_NAME=fs-066cf410af2428e2f.efs.eu-west-1.amazonaws.com
        export AWS_EFS_PACKS_DIR=packs
        export AWS_KEEP_EC2_INSTANCES=true
        export AWS_KEY_NAME=YOUR_AWS_KEYPAIR_NAME
        export AWS_INSTANCE_TYPE=t2.micro
        export AWS_INSTANCE_NAME=MY_AVH_INSTANCE

    * If ``AWS_AMI_VERSION`` is not set, the avhclient will use the latest available version of AVH AMI.
    * If ``AWS_EFS_DNS_NAME`` is set, the AVH Client will try to mount it during the cloud-init phase. The only scenario supported for now is using Packs.
    * If ``AWS_EFS_PACKS_DIR`` is set, the mount path is relative to ``/home/ubuntu`` folder. Default folder is `packs` and if it exists locally will be then replaced by the EFS mount. Only used when ``AWS_EFS_DNS_NAME`` env is set.

    AWS Cloudformation can be used to create the AWS resources required for AVH operation, as shown `in this template <https://github.com/ARM-software/AVH-GetStarted/tree/main/infrastructure/cloudformation>`_

* When **reusing an AVH Instance**::

    export AWS_INSTANCE_ID=YOUR_INSTANCE

Local Backend Setup
###################

Operation with a local backend requires no specific environment parameters, but assumes that necessary toolchain, AVH targets and utilities are installed locally on the machine and configured for execution in command line.

****

Usage
-----

Getting Help
############

To get the brief descriptions of all commands and options available with avhclient execute::

    avhclient -h

You can also use option ``-h`` with a specific command to get help for it. For example for ``execute`` command::

    avhclient execute -h

Execute command
###############

* Create a new AWS AVH instance and run AVH project
    The ``execute`` command bundles all necessary steps to build your
    avh project:

    * ``prepare`` the backend.
    * ``upload`` your files
    * ``run`` your commands
    * ``download`` the results
    * ``cleanup`` the backend

    Inform the path for the `avh.yml` file for your AVH project (example)::

        avhclient -b aws execute --specfile AVH-GetStarted/basic/avh.yml

* You can also run in AVH commands in your local computer by selecting `local` backend::

        avhclient -b local execute --specfile AVH-GetStarted/basic/avh.yml

* There are also backend specific info you can provide to the tool::

        avhclient -b aws -h (get full list)
        avhclient -b aws --instance-name MY_NEW_NAME execute --specfile AVH-GetStarted/basic/avh.yml (seeting a new AVH instance name)
        avhclient -b aws --ami-version 1.1.0 --specfile AVH-GetStarted/basic/avh.yml (Create a new AVH instance from a v1.1.0 AVH AMI)
        avhclient -b aws --ami-version >1.1.0 --specfile AVH-GetStarted/basic/avh.yml (Create a new AVH instance from a >v1.1.0 AVH AMI)

Execute with Docker
###################

To run avhclient in a Docker container one needs to create an environment file
(``env.txt``) with the following content::

    AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY
    AWS_IAM_PROFILE
    AWS_SECURITY_GROUP_ID
    AWS_SUBNET_ID
    AWS_S3_BUCKET_NAME
    AWS_DEFAULT_REGION
    AWS_AMI_ID
    AWS_AMI_VERSION
    AWS_KEEP_EC2_INSTANCES
    AWS_KEY_NAME
    AWS_INSTANCE_TYPE
    AWS_INSTANCE_NAME

This environment file is used to forward the local environment variables into
the Docker container. Having this prepared one can run ``avhclient`` in a
container as follows::

    docker run --rm -i --env-file ./env.txt \
        -v $(pwd):/workspace \
        -w /workspace \
        ghcr.io/arm-software/avhclient \
        avhclient [..]

The arguments are the same as above. If one requires more files from the Docker
host to be mapped into the container, this can be done like::

    docker run --rm -i --env-file ./env.txt \
        -v $HOME/.ssh:/root/.ssh \
        -v $HOME/.aws:/root/.aws \
        -v $(pwd):/workspace \
        -w /workspace \
        ghcr.io/arm-software/avhclient \
        avhclient [..]

This exposes the local user's SSH and AWS config files to the container.

****

AVH YML file syntax
-------------------

avhclient ``execute`` command requires a specfile in YML format that describes details of individual steps to be executed on AVH. The file syntax is explained below.

A JSON schema for automatic checks and auto-completion is in `schema/avh.schema.json <schema/avh.schema.json>`_.

Fields
######

.. code-block::

        Format of the specfile:
                name: (optional) The name of the workload.
                workdir: (optional) The local directory to use as the workspace, defaults to specfile's parent.
                backend: (optional) Dictionary with backend specific parameters.
                  aws: (optional) Dictionary with AWS backend specific parameters. (see backend help)
                  local: (optional) Dictionary with local backend specific parameters. (see backend help)
                upload: (optional) List of glob patterns of files (relative to workdir) to be sent to the AVH backend. (see glob format)
                steps: (mandatory) List of steps to be executed on the AVH backend.
                  - run: String written into a bash script and executed on the AVH backend inside the workspace directory.
                download: (optional) List of glob patterns of files (relative to workdir) to be retrieved back from the AVH backend. (see glob format)
            Glob format:
                The list of glob patterns is evaluated in order.
                Wildcard '*' matches all files but no directory except hidden files (starting with '.').
                Wildcard '**' matches all files and directories except hidden files/directories (starting with '.').
                Inclusive matches (no prefix) are added to the file list.
                Exclusive (prefixed with '-:') matches are removed from current file list.

Example
#######

.. code-block::

    # yaml-language-server: $schema=https://raw.githubusercontent.com/ARM-software/avhclient/main/schema/avh.schema.json

    name: "AVH GetStarted Example"
    workdir: ./
    backend:
      aws:
        ami-version: ~=1.1
        instance-type: t2.micro
    upload:
      - RTE/**/*
      - -:RTE/**/RTE_Components.h
      - basic.debug.cprj
      - build.py
      - main.c
      - requirements.txt
      - retarget_stdio.c
      - vht_config.txt
      - README.md
    steps:
      - run: |
          pip install -r requirements.txt
          python build.py --verbose build run
    download:
      - RTE/**/RTE_Components.h
      - Objects/basic.axf
      - Objects/basic.axf.map
      - basic-*.xunit
      - basic-*.zip

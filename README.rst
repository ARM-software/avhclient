|build-badge| |test-badge| |cov-badge| |python-badge|
|wheel-badge| |pypi-badge| |license-badge|

Arm Virtual Hardware Client
===========================

Installation
------------

Installing (development snapshot) directly from GitHub `main` branch::

    pip install git+https://github.com/ARM-software/avhclient.git@main

Copyright (C) 2022, Arm Ltd.

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

****

Backend Setup
-------------

AWS Backend Setup
#################
The AWS backend is built on top of `boto3` AWS SDK.

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
In order to avhclient is needed to expose some AWS resources for the tools.

* For a **new AVH instance**:
    Mandatory info::

        export AWS_IAM_PROFILE='YOUR_IAM_PROFILE'
        export AWS_SECURITY_GROUP_ID='YOUR_AWS_SECURITY_GROUP_ID'
        export AWS_SUBNET_ID='YOUR_SECURITY_GROUP_ID'
        export AWS_S3_BUCKET_NAME='YOUR_B3_BUCKET_NAME'

    Optional info (examples)::

        export AWS_AMI_ID=DESIRED_AVH_AMI_ID
        export AWS_AMI_VERSION=1.1.2
        export AWS_KEEP_EC2_INSTANCES=true
        export AWS_KEY_NAME=YOUR_AWS_KEYPAIR_NAME
        export AWS_INSTANCE_TYPE=t2.micro
        export AWS_INSTANCE_NAME=MY_AVH_INSTANCE

    In case `AWS_AMI_VERSION` is not set, the avhclient will the latest AVH AMI available.

    In addition, a `Cloudformation` code can be used to create the AVH dependencies for
    your account `here <https://github.com/ARM-software/VHT-GetStarted/tree/main/infrastructure/cloudformation>`_

* When **reusing an AVH Instance**::

    export AWS_INSTANCE_ID=YOUR_INSTANCE

****

Usage
-----

Select backend
##############
The `avhclient` supports currently `local` and `aws` (default) backend. ::

    avhclient -b aws
    avhclient -b local

Execute command
###############

* Getting help for a specific command (e.g. `execute`)::

    avhclient -b aws execute -h

* Create a new AWS AVH instance and run AVH project
    The `execute` command bundles all necessary steps to build your
    avh project:

    * prepare the backend.
    * upload your files
    * run your commands
    * download the results
    * cleanup the backend

    Inform the path for the `avh.yml` file for your AVH project (example)::

        avhclient -b aws execute --specfile VHT-GetStarted/basic/avh.yml

* You can also run in AVH commands in your local computer by selecting `local` backend::

        avhclient -b local execute --specfile VHT-GetStarted/basic/avh.yml

* There are also backend specific info you can provide to the tool::

        avhclient -b aws -h (get full list)
        avhclient -b aws --instance-name MY_NEW_NAME execute --specfile VHT-GetStarted/basic/avh.yml (seeting a new AVH instance name)
        avhclient -b aws --ami-version 1.1.0 --specfile VHT-GetStarted/basic/avh.yml (Create a new VHT instance from a v1.1.0 AVH AMI)
        avhclient -b aws --ami-version >1.1.0 --specfile VHT-GetStarted/basic/avh.yml (Create a new VHT instance from a >v1.1.0 AVH AMI)

****

AVH YML file syntax
-------------------

Fields
######

.. code-block::

        Format of the specfile:
                name: (optional) The name of the workload.
                workdir: (optional) The local directory to use as the workspace, defaults to specfile's parent.
                backend: (optional) Dictionary with backend specific parameters.
                  aws: (optional) Dictionary with AWS backend specific parameters. (see backend help)
                  local: (optional) Dictionary with local backend specific parameters. (see backend help)
                upload: (optional) List of glob patterns of files to be sent to the AVH backend. (see glob format)
                steps: (mandatory) List of steps to be executed on the AVH backend.
                  - run: String written into a bash script and executed on the AVH backend inside the workspace directory.
                download: (optional) List of glob patterns of files to be retrieved back from the AVH backend. (see glob format)
            Glob format:
                The list of glob patterns is evaluated in order.
                Wildcard '*' matches all files but no directory except hidden files (starting with '.').
                Wildcard '**' matches all files and directories except hidden files/directories (starting with '.').
                Inclusive matches (no prefix) are added to the file list.
                Exclusive (prefixed with '-:') matches are removed from current file list.

Example
#######

.. code-block::

    name: "VHT GetStarted Example"
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

****

AVH Projects using AVH Client
-----------------------------

* `VHT-GetStarted <https://github.com/ARM-software/VHT-GetStarted>`_
* `CMSIS-RTOS2-Validation <https://github.com/ARM-software/CMSIS-RTOS2_Validation>`_

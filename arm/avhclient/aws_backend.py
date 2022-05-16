# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Arm Ltd. All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0
#

import logging
import os
import time

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List, Union

import boto3

from botocore.exceptions import ClientError
from botocore.exceptions import WaiterError
from semantic_version import Version, SimpleSpec

from .avh_backend import AvhBackend, AvhBackendState


class AwsBackend(AvhBackend):
    """
       AVH AWS Backend

       This backend runs in your Amazon account:
        * Creates/starts/setup a [new] AVH EC2 instance.
        * Run AVH-related commands.
        * Get the outputs
        * Terminates/Stops the AVH EC2 instance.

       The AWS credentials key is expected as envs. See _is_aws_credentials_present method.
       Some AWS-related info is expected as envs. See _setup.
   """

    AMI_WORKDIR = '/home/ubuntu'

    @staticmethod
    def name() -> str:
        return "aws"

    @staticmethod
    def priority() -> int:
        return 10

    @property
    def ami_id(self) -> str:
        """Amazon Machine Image ID (AWS_AMI_ID)."""
        return self._ami_id or os.environ.get('AWS_AMI_ID', '')

    @ami_id.setter
    def ami_id(self, value: str):
        self._ami_id = value

    @property
    def ami_version(self) -> str:
        """Amazon Machine Image version (AWS_AMI_VERSION). Must be a valid PEP-440 version specifier."""
        return self._ami_version or os.environ.get('AWS_AMI_VERSION', '==*')

    @ami_version.setter
    def ami_version(self, value: str):
        self._ami_version = value

    @property
    def default_region(self) -> str:
        "AWS Default Region (AWS_DEFAULT_REGION)"
        return self._default_region or os.environ.get('AWS_DEFAULT_REGION', 'eu-west-1')

    @default_region.setter
    def default_region(self, value: str):
        self._default_region = value

    @property
    def efs_dns_name(self) -> str:
        """AWS EFS DNS Name e.g. fs-086c927c9d324a69f.efs.eu-west-1.amazonaws.com"""
        return self._efs_dns_name or os.environ.get('AWS_EFS_DNS_NAME', '')

    @efs_dns_name.setter
    def efs_dns_name(self, value: str):
        self._efs_dns_name = value

    @property
    def efs_packs_dir(self) -> str:
        """AWS EFS Packs Folder e.g. packs. Default: packs"""
        return self._efs_packs_dir or os.environ.get('AWS_EFS_PACK_DIR', 'packs')

    @efs_packs_dir.setter
    def efs_packs_dir(self, value: str):
        self._efs_packs_dir = value

    @property
    def iam_profile(self) -> str:
        """Amazon IAM profile (AWS_IAM_PROFILE)."""
        return self._iam_profile or os.environ.get('AWS_IAM_PROFILE', '')

    @iam_profile.setter
    def iam_profile(self, value: str):
        self._iam_profile = value

    @property
    def instance_name(self) -> str:
        """Amazon EC2 instance name (AWS_INSTANCE_NAME)."""
        return self._instance_name or os.environ.get('AWS_INSTANCE_NAME', '')

    @instance_name.setter
    def instance_name(self, value: str):
        self._instance_name = value

    @property
    def instance_id(self) -> str:
        """Amazon EC2 instance id (AWS_INSTANCE_ID)."""
        return self._instance_id or os.environ.get('AWS_INSTANCE_ID', '')

    @instance_id.setter
    def instance_id(self, value: str):
        self._instance_id = value

    @property
    def instance_type(self) -> str:
        """Amazon EC2 instance type (AWS_INSTANCE_TYPE)."""
        return self._instance_type or os.environ.get('AWS_INSTANCE_TYPE', 'c5.large')

    @instance_type.setter
    def instance_type(self, value: str):
        self._instance_type = value

    @property
    def key_name(self) -> str:
        """Amazon EC2 SSH key name (AWS_KEY_NAME)."""
        return self._key_name or os.environ.get('AWS_KEY_NAME', '')

    @key_name.setter
    def key_name(self, value: str):
        self._key_name = value

    @property
    def s3_bucket_name(self) -> str:
        """Amazon S3 bucket name (AWS_S3_BUCKET_NAME)."""
        return self._s3_bucket_name or os.environ.get('AWS_S3_BUCKET_NAME', '')

    @s3_bucket_name.setter
    def s3_bucket_name(self, value: str):
        self._s3_bucket_name = value

    @property
    def security_group_id(self) -> str:
        """Amazon EC2 security group id (AWS_SECURITY_GROUP_ID)."""
        return self._security_group_id or os.environ.get('AWS_SECURITY_GROUP_ID', '')

    @security_group_id.setter
    def security_group_id(self, value: str):
        self._security_group_id = value

    @property
    def subnet_id(self) -> str:
        """Amazon EC2 subnet id (AWS_SUBNET_ID)."""
        return self._subnet_id or os.environ.get('AWS_SUBNET_ID', '')

    @subnet_id.setter
    def subnet_id(self, value: str):
        self._subnet_id = value

    @property
    def keep_ec2_instance(self) -> bool:
        """Keep the EC2 instance running or terminate? (AWS_KEEP_EC2_INSTANCES)."""
        return self._keep_ec2_instance or (os.environ.get('AWS_KEEP_EC2_INSTANCES', 'false').lower() == 'true')

    @keep_ec2_instance.setter
    def keep_ec2_instance(self, value: bool):
        self._keep_ec2_instance = value

    @property
    def s3_keyprefix(self) -> bool:
        """Amazon S3 storage key prefix (AWS_S3_KEYPREFIX)."""
        return self._s3_keyprefix or os.environ.get('AWS_S3_KEYPREFIX', 'ssm')

    @s3_keyprefix.setter
    def s3_keyprefix(self, value: bool):
        self._s3_keyprefix = value

    def __init__(self):
        self._ami_id = None
        self._ami_version = None
        self._default_region = None
        self._efs_dns_name = None
        self._efs_packs_dir = None
        self._iam_profile = None
        self._instance_name = None
        self._instance_id = None
        self._instance_type = None
        self._key_name = None
        self._s3_bucket_name = None
        self._security_group_id = None
        self._subnet_id = None
        self._keep_ec2_instance = None
        self._s3_keyprefix = None

    def __repr__(self):
        return (
            f"ami_id={self.ami_id},"
            f"ami_version={self.ami_version},"
            f"default_region={self.default_region},"
            f"efs_dns_name={self.efs_dns_name},"
            f"efs_packs_dir={self.efs_packs_dir},"
            f"iam_profile={self.iam_profile},"
            f"instance_name={self.instance_name},"
            f"instance_id={self.instance_id},"
            f"instance_type={self.instance_type},"
            f"key_name={self.key_name},"
            f"s3_bucket_name={self.s3_bucket_name},"
            f"security_group_id={self.security_group_id},"
            f"subnet_id={self.subnet_id},"
            f"keep_ec2_instance={self.keep_ec2_instance}"
        )

    def _init(self):
        self._init = lambda: None

        self._is_aws_credentials_present()

        logging.debug('aws:Creating EC2 client...')
        self._ec2_client = boto3.client('ec2')

        logging.debug('aws:Creating SSM client...')
        self._ssm_client = boto3.client('ssm')

        logging.debug('aws:Creating S3 client...')
        self._s3_client = boto3.client('s3')

        logging.debug('aws:Creating S3 resource...')
        self._s3_resource = boto3.resource('s3')

        self._setup()

    @staticmethod
    def _check_env(key) -> bool:
        if key in os.environ:
            logging.debug("aws:%s present!", key)
            return True
        logging.warning("aws:%s environment variable not present!", key)
        return False

    def _is_aws_credentials_present(self):
        """
            Verifies presence of AWS Credentias as Environment Variables.
            AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are mandatory
            AWS_SESSION_TOKEN is optional for IAM User credentials.
        """
        self._check_env('AWS_ACCESS_KEY_ID')
        self._check_env('AWS_SECRET_ACCESS_KEY')
        self._check_env('AWS_DEFAULT_REGION')
        if not self._check_env('AWS_SESSION_TOKEN'):
            logging.debug('aws:It is expected for an IAM User')

    def _get_efs_packs_user_data(self) -> str:
        """
        Return the user data to mount the EFS packs in the EC2 instace
        This is run in the EC2 cloud-init phase.
        """
        return ("#cloud-config\n"
            "package_update: false\n"
            "package_upgrade: false\n"
            "runcmd:\n"
            "- ubuntu_folder=/home/ubuntu\n"
            "- efs_mount_point_1=/mnt/efs/fs1\n"
            f"- file_system_id_1={self.efs_dns_name.split('.')[0]}\n"
            f"- efs_dns_name={self.efs_dns_name}\n"
            f"- pack_folder={self.efs_packs_dir}\n"
            "- yum install -y amazon-efs-utils\n"
            "- apt-get -y install amazon-efs-utils\n"
            "- yum install -y nfs-utils\n"
            "- apt-get -y install nfs-common\n"
            "- mkdir -p \"${efs_mount_point_1}\"\n"
            "- test -f \"/sbin/mount.efs\" && printf \"\\n${file_system_id_1}:/ ${efs_mount_point_1} efs tls,_netdev\\n\" >> /etc/fstab || printf \"\\n${efs_dns_name}:/ ${efs_mount_point_1} nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport,_netdev 0 0\\n\" >> /etc/fstab\n"
            "- test -f \"/sbin/mount.efs\" && grep -ozP 'client-info]\\nsource' '/etc/amazon/efs/efs-utils.conf'; if [[ $? == 1 ]]; then printf \"\\n[client-info]\\nsource=liw\\n\" >> /etc/amazon/efs/efs-utils.conf; fi;\n"
            "- retryCnt=15; waitTime=30; while true; do mount -a -t efs,nfs4 defaults; if [ $? = 0 ] || [ $retryCnt -lt 1 ]; then echo File system mounted successfully; break; fi; echo File system not available, retrying to mount.; ((retryCnt--)); sleep $waitTime; done;\n"
            "- rm -rf \"${ubuntu_folder}/${pack_folder}\"\n"
            "- mkdir -p \"${ubuntu_folder}/${pack_folder}\"\n"
            "- chown -R ubuntu:ubuntu \"${ubuntu_folder}/${pack_folder}\"\n"
            "- mount -t nfs -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport ${efs_dns_name}:/${pack_folder} ${ubuntu_folder}/${pack_folder}\n"
            "- printf \"\\n${efs_dns_name}:/${pack_folder} ${ubuntu_folder}/${pack_folder} nfs4 nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=600,retrans=2,noresvport,_netdev 0 0\\n\" >> /etc/fstab\n"
        )

    def _setup(self):
        """
            Setup AWS object by collecting env vars & preparing AWS instance
        """
        # Initializing None all AVH related variables
        logging.debug("aws:setting up aws backend")

        # EC2-related info is not needed if an instance is already created
        if self.instance_name and not self.instance_id:
            self.instance_id = self.find_instance_by_name(self.instance_name)

        if not self.instance_id:
            if not self.instance_name:
                user = os.environ.get('USER', os.environ.get('USERNAME', "unknown"))
                host = os.environ.get('HOSTNAME', "unknown")
                self.instance_name = f"{user}@{host}"

            if not self.ami_id:
                self.ami_id = self.get_image_id()
            if not self.ami_id:
                logging.error('AWS_AMI_ID must not be blank. You should inform either AWS_AMI_ID or provide a valid AWS_AMI_VERSION')
                raise RuntimeError('AWS_AMI_ID must not be blank. You should inform either AWS_AMI_ID or provide a valid AWS_AMI_VERSION')

            if not self.iam_profile:
                logging.error("aws:environment variable `AWS_IAM_PROFILE` needs to be present!")
                raise RuntimeError("aws:environment variable `AWS_IAM_PROFILE` needs to be present!")
            if not self.security_group_id:
                logging.error("aws:environment variable `AWS_SECURITY_GROUP_ID` needs to be present!")
                raise RuntimeError("aws:environment variable `AWS_SECURITY_GROUP_ID` needs to be present!")
            if not self.subnet_id:
                logging.error("aws:environment variable `AWS_SUBNET_ID` needs to be present!")
                raise RuntimeError("aws:environment variable `AWS_SUBNET_ID` needs to be present!")

        if not self.s3_bucket_name:
            logging.error("aws:environment variable `AWS_S3_BUCKET_NAME` needs to be present!")
            raise RuntimeError("aws:environment variable `AWS_S3_BUCKET_NAME` needs to be present!")

        if self.efs_dns_name:
            logging.info("aws:EFS DNS %s is going to be mounted", self.efs_dns_name)
            logging.info("aws:Local packs directory will be replace by EFS packs folder named %s", self.efs_packs_dir)

        logging.debug("aws:aws__repr__:%s", self.__repr__())
        logging.info("aws:Backend successfully initialized!")

    def find_instance_by_name(self, name: str) -> Union[str, None]:
        """Find an instance by name attribute.
        The result is None if more than one instance with the given name exists.

        Params:
            name - The name of a machine instance to lookup.

        Returns:
            The machine id or None
        """
        instance_id = None
        name_filter = [
            {'Name': 'tag:Name', 'Values': [name]},
            {'Name': 'instance-state-name', 'Values': ['running', 'stopped']}
        ]
        response = self._ec2_client.describe_instances(Filters=name_filter)

        if 'Reservations' not in response:
            logging.debug("Response doesn't contain element 'Reservations'")
        elif len(response['Reservations']) == 0:
            logging.debug("Response doesn't contain elements in 'Reservations'")
        elif len(response['Reservations']) > 1:
            logging.warning("Cannot identify EC2 instance by name '%s' due to ambiguity!", self.instance_name)
        elif 'Instances' not in response['Reservations'][0]:
            logging.debug("Response doesn't contain element 'Instances' in 'Reservations'")
        elif len(response['Reservations'][0]['Instances']) != 1:
            logging.debug("Response doesn't contain single instance in 'Reservations'")
        elif 'InstanceId' not in response['Reservations'][0]['Instances'][0]:
            logging.debug("Response doesn't contain element 'InstanceId' in 'Instances'")
        else:
            instance_id = response['Reservations'][0]['Instances'][0]['InstanceId']
            logging.info("aws:Resolved EC2 instance name %s as instance ID %s", name, instance_id)
        return instance_id

    def create_instance(self):
        """
            Create an EC2 Instance. It is a wrapper for create_ec2_instance.
            If key_name is present, it creates a instance with the selected private key.

            This is a mandatory AVH backend method.
        """
        self._init()
        self.instance_id = self.create_ec2_instance(
            ImageId=self.ami_id,
            InstanceType=self.instance_type,
            MaxCount=1,
            MinCount=1,
            NetworkInterfaces=[{
                'AssociatePublicIpAddress': True,
                'DeleteOnTermination': True,
                'Description':'AVH Network Instance',
                'DeviceIndex': 0,
                'Groups': [self.security_group_id],
                'SubnetId': self.subnet_id
            }],
            KeyName=self.key_name,
            TagSpecifications=[{'ResourceType': 'instance', 'Tags': [
                {'Key': 'Name', 'Value': self.instance_name},
                {'Key': 'AVH_CLI', 'Value': 'true'}
            ]}],
            UserData=self._get_efs_packs_user_data() if self.efs_dns_name != '' else '',
            IamInstanceProfile={'Name': self.iam_profile}
        )

        return self.instance_id

    def create_ec2_instance(self, **kwargs):
        """
        Create a new EC2 Instance

        Parameters
        ----------
        **kwargs: Keyword args associated with run-instances API doc e.g.:
            --create-ec2-instance
                ImageId=ami-0c5eeabe11f3a2685 \
                InstanceType=t2.micro \
                MaxCount=1 \
                MinCount=1 \
                SecurityGroupIds=['sg-04022e04e91197ce3'] \
                SubnetId=subnet-00455495b268076f0  \
                IamInstanceProfile="{'Name': 'Proj-s3-orta-vht-role'}"

        Returns
        -------
        string
            Instance ID

        More
        ----
        API Definition
            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.run_instances
        """
        kwargs = {k: v for k, v in kwargs.items() if v}

        logging.debug('aws:DryRun=True to test for permission check')
        logging.debug("aws:create_ec2_instance:kwargs:%s", kwargs)

        try:
            self._ec2_client.run_instances(**kwargs, DryRun=True)
        except ClientError as e:
            if 'DryRunOperation' not in str(e):
                raise RuntimeError from e

        logging.info('aws:Creating EC2 instance...')
        try:
            response = self._ec2_client.run_instances(**kwargs)
        except ClientError as e:
            raise RuntimeError from e
        logging.debug(response)

        self.instance_id = response['Instances'][0]['InstanceId']
        assert isinstance(self.instance_id, str)
        self.wait_ec2_running()
        self.wait_ec2_status_ok()
        logging.info("aws:EC2 instance %s created!", self.instance_id)
        return self.instance_id

    def delete_file_from_cloud(self, key):
        """
        Delete S3 Object

        Parameters
        ----------
        String
            key (s3 path)

        More
        ----
        API Definition
            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.delete_object

        This is a mandatory AVH backend method.
        """
        self._init()
        logging.debug("aws:Delete S3 Object from S3 Bucket %s, Key %s", self.s3_bucket_name, key)
        try:
            response = self._s3_client.delete_object(
                Bucket=self.s3_bucket_name,
                Key=key
            )
        except ClientError as e:
            raise RuntimeError from e
        logging.debug(response)

    def download_file_from_cloud(self, filename, key):
        """
        Download S3 File

        Parameters
        ----------
        String
            filename (destination local path)
            key (s3 path)

        More
        ----
        API Definition
            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.download_file

        This is a mandatory AVH backend method.
        """
        self._init()
        try:
            logging.debug("aws:Downloading S3 file from bucket %s , key %s, filename %s", self.s3_bucket_name, key, filename)
            self._s3_client.download_file(self.s3_bucket_name, key, filename)
        except ClientError as e:
            if 'HeadObject operation: Not Found' in str(e):
                logging.error("Key '%s' not found on S3 Bucket Name = '%s'", key, self.s3_bucket_name)
            raise RuntimeError from e

    def get_image_id(self):
        """
        Get the AVH AMI ID for the region
        The AVH AMI ID changes for each AWS region

        Return
        ----------
        String
            AVH AMI ID

        More
        ----
        API Definition
            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_images

        This is a mandatory AVH backend method.
        """
        assert self.ami_version is not None, \
            "The variable `ami_version` is not present"

        try:
            response = self._ec2_client.describe_images(
                Filters=[
                    {
                        'Name': 'name',
                        'Values': ["ArmVirtualHardware-*"]
                    },
                ]
            )
        except ClientError as e:
            raise RuntimeError from e

        logging.debug("aws:get_vht_ami_id_by_version:%s", response)

        version_spec = SimpleSpec(self.ami_version)
        images = {}
        for image in response['Images']:
            ver = image['Name'].split('-')[1]
            try:
                images[Version(ver)] = image['ImageId']
            except ValueError:
                logging.debug("aws:get_vht_ami_id_by_version:Invalid version identifier found: %s", ver)
        versions = sorted(version_spec.filter(images.keys()), reverse=True)

        if not versions:
            logging.error("aws:get_vht_ami_id_by_version:No AMI found matching version spec %s", self.ami_version)
            logging.error("aws:get_vht_ami_id_by_version:Available AMI versions %s",
                          sorted([str(k) for k, v in images.items()], reverse=True))
            raise RuntimeError()

        self.ami_id = images[versions[0]]
        logging.info("aws:Selecting AMI version %s, AMI ID %s", versions[0], self.ami_id)
        return self.ami_id

    def get_instance_state(self):
        """
        Get EC2 Instance State

        Return
        ----------
        String
            EC2 Instance State ('pending'|'running'|'shutting-down'|'terminated'|'stopping'|'stopped')

        More
        ----
        API Definition
            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_instances
        """
        self._init()

        try:
            response = self._ec2_client.describe_instances(
                InstanceIds=[
                    self.instance_id,
                ],
            )
        except ClientError as e:
            raise RuntimeError from e

        logging.debug("aws:get_instance_state: %s", response)
        instance_state = response['Reservations'][0]['Instances'][0]['State']['Name']
        logging.debug("aws:The EC2 instance state is %s...", instance_state)
        return instance_state

    def get_s3_file_content(self, key):
        """
        Get S3 File Content

        Parameters
        ----------
        String
            key (s3 path)

        Return
        ----------
        String
            S3 File Content

        More
        ----
        API Definition
            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#object
        """
        self._init()
        content = ''
        try:
            content = self._s3_resource.Object(self.s3_bucket_name, key).get()['Body'].read().decode('utf-8')
        except self._s3_client.exceptions.NoSuchKey:
            logging.debug("aws:Key '%s' not found on S3 bucket '%s'", key, self.s3_bucket_name)
        return content

    def get_s3_ssm_command_id_key(self, command_id, output_type):
        """
        Get calculated S3 SSM Command ID Output Key

        Parameters
        ----------
        String
            command_id (Command ID)
            output_type (`stderr` or `stdout`)

        Return
        ----------
        String
            S3 SSM Command ID Key
        """
        return f"{self.s3_keyprefix}/{command_id}/{self.instance_id}/awsrunShellScript/0.awsrunShellScript/{output_type}"

    def get_ssm_command_id_status(self, command_id):
        """
        Get the Status for a specific command ID and Instance ID.

        Parameters
        ----------
        String
            command_id (Command ID)

        Return
        ----------
        String
            Command ID Status

        More
        ----------
        API Definition:
            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ssm.html#SSM.Client.list_commands
        """

        try:
            response = self._ssm_client.list_commands(
                CommandId=command_id
            )
        except ClientError as e:
            raise RuntimeError from e

        logging.debug("aws:get_ssm_command_id_status:%s", response)
        command_id_status = response['Commands'][0]['Status']
        logging.debug("aws:The command_id %s status is %s...", command_id, command_id_status)
        return command_id_status

    def get_ssm_command_id_status_details(self, command_id):
        """
        Get the Status details for a specific command ID and Instance ID.

        Parameters
        ----------
        String
            command_id (Command ID)

        Return
        ----------
        String
            Command ID Status Details

        More
        ----------
        API Definition:
            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ssm.html#SSM.Client.get_command_invocation
        """

        try:
            response = self._ssm_client.get_command_invocation(
                CommandId=command_id,
                InstanceId=self.instance_id
            )
        except ClientError as e:
            raise RuntimeError from e

        logging.debug("aws:get_ssm_command_id_status_details:%s", response)
        logging.info("aws:The command_id %s status details is %s ...", command_id, response['StatusDetails'])
        return response['StatusDetails']

    def get_ssm_command_id_stdout_url(self, command_id):
        """
        Get the stdout output URL for a specific command ID and Instance ID.

        Parameters
        ----------
        String
            command_id (Command ID)

        Return
        ----------
        String
            Command ID Stdout URL

        More
        ----------
        API Definition
            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ssm.html#SSM.Client.list_command_invocations
        """
        try:
            response = self._ssm_client.list_command_invocations(
                CommandId=command_id,
                InstanceId=self.instance_id
            )
        except ClientError as e:
            raise RuntimeError from e

        logging.debug("aws:get_ssm_command_id_stdout_url:%s", response)
        return response['CommandInvocations'][0]['StandardOutputUrl']

    def get_ssm_command_id_stderr_url(self, command_id):
        """
        Get the stderr output URL for a specific command ID and Instance ID.

        Parameters
        ----------
        String
            command_id (Command ID)

        Return
        ----------
        String
            Command ID Stderr URL

        More
        ----------
        API Definition
            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ssm.html#SSM.Client.list_command_invocations
        """
        try:
            response = self._ssm_client.list_command_invocations(
                CommandId=command_id,
                InstanceId=self.instance_id
            )
        except ClientError as e:
            raise RuntimeError from e

        logging.debug("aws:get_ssm_command_id_stderr_url:%s", response)
        return response['CommandInvocations'][0]['StandardErrorUrl']

    def create_or_start_instance(self) -> AvhBackendState:
        """Create a new or start an existing machine instance

        Returns:
            The machine instance state.
        """
        self._init()
        if self.instance_id:
            state = self.get_instance_state()
            if state == "running":
                logging.debug("aws:EC2 Instance %s already running!", self.instance_id)
                return AvhBackendState.RUNNING
            if state == "stopped":
                logging.debug("aws:EC2 Instance %s provided!", self.instance_id)
                self.start_instance()
                return AvhBackendState.STARTED
            logging.warning("aws:EC2 Instance %s cannot be reused from state %s!", self.instance_id, state)

        self.create_instance()
        return AvhBackendState.CREATED

    def prepare(self, force: bool = False) -> AvhBackendState:
        self._init()
        state = self.create_or_start_instance()
        if state == AvhBackendState.CREATED or force:
            logging.info("aws:Setting up the instance...")
            commands = [
                f"runuser -l ubuntu -c 'cat ~/.bashrc | grep export > {self.AMI_WORKDIR}/vars'",
                f"runuser -l ubuntu -c 'mkdir -p {self.AMI_WORKDIR}/packs/.Web'",
                f"runuser -l ubuntu -c 'wget -N https://www.keil.com/pack/index.pidx -O {self.AMI_WORKDIR}/packs/.Web/index.pidx'",
                "apt update",
                "apt install awscli -y"
            ]
            self.send_remote_command_batch(
                commands,
                working_dir=self.AMI_WORKDIR,
                fail_if_unsuccess=True,
                enable_logging_info=False)

        logging.info("aws:Setting up instance workspace...")
        commands = [
            f"runuser -l ubuntu -c 'rm -rf {self.AMI_WORKDIR}/workspace'",
            f"runuser -l ubuntu -c 'mkdir -p {self.AMI_WORKDIR}/workspace'"
        ]
        self.send_remote_command_batch(
            commands,
            working_dir=self.AMI_WORKDIR,
            fail_if_unsuccess=True,
            enable_logging_info=False)

        return state

    def run_commands(self, cmds: List[str]):
        self._init()

        shfile = Path(NamedTemporaryFile(prefix="script-", suffix=".sh", delete=False).name)
        try:
            with open(shfile, mode="w", encoding='UTF-8', newline='\n') as file:
                file.write("#!/bin/bash\n")
                file.write("set +x\n")
                file.write("\n".join(cmds))
                file.write("\n")

            self.upload_file_to_cloud(str(shfile), shfile.name)

            # commands which do not need to go to INFO
            commands = [
                f"runuser -l ubuntu -c 'aws s3 cp s3://{self.s3_bucket_name}/{shfile.name} "
                f"{self.AMI_WORKDIR}/{shfile.name} --region {self.default_region} && "
                f"chmod +x {self.AMI_WORKDIR}/{shfile.name}'"
            ]
            self.send_remote_command_batch(
                commands,
                working_dir=self.AMI_WORKDIR,
                fail_if_unsuccess=True,
                enable_logging_info=False)

            # commands which need to go to INFO
            commands = [
                f"runuser -l ubuntu -c 'source {self.AMI_WORKDIR}/vars "
                f"&& pushd {self.AMI_WORKDIR}/workspace && {self.AMI_WORKDIR}/{shfile.name}'"
            ]
            self.send_remote_command_batch(
                commands,
                working_dir=self.AMI_WORKDIR,
                fail_if_unsuccess=True,
                enable_logging_info=True)

        finally:
            os.unlink(shfile)
            self.delete_file_from_cloud(shfile.name)

    def upload_workspace(self, filename: Union[str, Path]):
        self._init()
        if isinstance(filename, str):
            filename = Path(filename)
        try:
            self.upload_file_to_cloud(str(filename), filename.name)
            commands = [
                f"runuser -l ubuntu -c 'aws s3 cp s3://{self.s3_bucket_name}/{filename.name} {self.AMI_WORKDIR}/{filename.name} --region {self.default_region}'",
                f"runuser -l ubuntu -c 'cd {self.AMI_WORKDIR}/workspace; tar xf {self.AMI_WORKDIR}/{filename.name}'",
                f"runuser -l ubuntu -c 'rm -f {self.AMI_WORKDIR}/{filename.name}'"
            ]
            self.send_remote_command_batch(
                commands,
                working_dir=self.AMI_WORKDIR,
                fail_if_unsuccess=True,
                enable_logging_info=False)
        finally:
            self.delete_file_from_cloud(filename.name)

    def download_workspace(self, filename: Union[str, Path], globs: List[str] = None):
        if not globs:
            globs = ['**/*']
        self._init()
        if isinstance(filename, str):
            filename = Path(filename)
        try:
            tarbz2 = [f"rm -f {self.AMI_WORKDIR}/{filename.stem}.tar"]
            for pattern in globs:
                if pattern.startswith("-:"):
                    tarbz2.append(f"tar df {self.AMI_WORKDIR}/{filename.stem}.tar $(find {pattern[2:]} -type f)")
                else:
                    tarbz2.append(f"tar uf {self.AMI_WORKDIR}/{filename.stem}.tar $(find {pattern} -type f)")
            tarbz2.append(f"bzip2 {self.AMI_WORKDIR}/{filename.stem}.tar")

            commands = [
                f"runuser -l ubuntu -c 'cd {self.AMI_WORKDIR}/workspace; {'; '.join(tarbz2)}'",
                f"runuser -l ubuntu -c 'aws s3 cp {self.AMI_WORKDIR}/{filename.stem}.tar.bz2 s3://{self.s3_bucket_name}/{filename.name} --region {self.default_region}'",
                f"runuser -l ubuntu -c 'rm -f {self.AMI_WORKDIR}/{filename.stem}.tar.bz2'",
            ]
            self.send_remote_command_batch(
                commands,
                working_dir=self.AMI_WORKDIR,
                fail_if_unsuccess=True,
                enable_logging_info=False)
            self.download_file_from_cloud(str(filename), filename.name)
        finally:
            self.delete_file_from_cloud(filename.name)

    def upload_file_to_cloud(self, filename, key):
        """
        Upload a file to a S3 Bucket

        Parameters
        ----------
            filename: Local Filename Path
            key: Filepath to be stored on S3 Bucket

        More
        ----------
        API Definition
            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.upload_file
        """
        self._init()
        logging.debug("aws:Upload File %s to S3 Bucket %s, Key %s", filename, self.s3_bucket_name, key)
        self._s3_resource.meta.client.upload_file(filename, self.s3_bucket_name, key)

    def send_remote_command(
            self,
            command_list,
            working_dir,
            fail_if_unsuccess=True,
            enable_logging_info=True):

        """
        Send a remote command to an EC2 Instance.

        Parameters
        ----------
        List
            command_list (List of commands)
        String
            working_dir (Directory where the remote command will be executed)
        Boolean
            fail_if_unsuccess (Fail the method in case the command failed)
            enable_logging_info (Enable or disable command logging)

        Return
        ------
            JSON data from send_ssm_shell_command method.

        This is a mandatory AVH backend method.
        """
        self._init()
        logging.debug("aws:command_list = %s", command_list)
        response = self.send_ssm_shell_command(
            command_list=command_list,
            working_dir=working_dir
        )

        logging.log(logging.INFO if enable_logging_info else logging.DEBUG, '='*80)
        for i in response.keys():
            logging.log(logging.INFO if enable_logging_info else logging.DEBUG,
                "aws:send_remote_command:%s = %s", i, response[i].strip())

        if response['CommandIdStatus'] != 'Success' and fail_if_unsuccess:
            logging.error("aws:send_remote_command:Command %s failed!", command_list)
            logging.error("aws:send_remote_command:response\n%s", response)
            raise RuntimeError()
        return response

    def send_remote_command_batch(
            self,
            command_list,
            working_dir,
            fail_if_unsuccess=True,
            enable_logging_info=True):

        """
        Send batch of remote commands to an EC2 Instance.

        Parameters
        ----------
        List
            command_list (List of List of commands)
        String
            working_dir (Directory where the remote command will be executed)
        Boolean
            fail_if_unsuccess (Fail the method in case the command failed - Default: True)
            enable_logging_info (Enable or disable command logging)

        Return
        ------
            JSON data from send_ssm_shell_command method.

        This is a mandatory AVH backend method.
        """
        self._init()
        logging.debug("aws: command_list = %s", command_list)
        all_responses = []

        for command in command_list:
            all_responses.append(
                self.send_remote_command(
                    command_list=command,
                    working_dir=working_dir,
                    fail_if_unsuccess=fail_if_unsuccess,
                    enable_logging_info=enable_logging_info))

        logging.debug("aws: all_responses = %s", all_responses)
        return all_responses

    def send_ssm_shell_command(
            self,
            command_list,
            working_dir='/',
            return_type='all',
            timeout_seconds=600):
        """
        Send SSM Shell Commands to a EC2 Instance

        Parameters
        ----------
        String
            command_list (List of commands to be executed on the instance_id)
            working_dir (Working directory - Default: '/')
            return_type (
                Method return types:
                    `all`: Return as a dict: 'CommandId', 'CommandIdStatus', 'CommandList', 'StdOut', 'StdErr' - Default
                    `command_id`: Return only the `command_id` as a String
            )
            timeout_seconds (Command Timeout in Seconds - Default: 600)

        Return
        ----------
        Dict
            if return_type == `all` (Default):
                'CommandId', 'CommandIdStatus', 'CommandList', 'StdOut', 'StdErr'
        String
            if return_type == `command_id`:
                command_id

        More
        ----------
        TODO: Use **kwargs

        API Definition
            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ssm.html#SSM.Client.send_command
            https://docs.aws.amazon.com/systems-manager/latest/userguide/ssm-plugins.html#aws-runShellScript
        """

        logging.debug("aws:send_ssm_shell_command:%s:%s", working_dir, command_list)

        try:
            response = self._ssm_client.send_command(
                InstanceIds=[
                    self.instance_id
                ],
                DocumentName='AWS-RunShellScript',
                Parameters={
                    'workingDirectory': [
                        working_dir,
                    ],
                    'commands': [
                        command_list,
                    ]
                },
                OutputS3BucketName=self.s3_bucket_name,
                OutputS3KeyPrefix=self.s3_keyprefix,
                TimeoutSeconds=timeout_seconds,
            )
        except ClientError as e:
            raise RuntimeError from e

        logging.debug("aws:send_ssm_shell_command:%s", response)
        command_id = response['Command']['CommandId']
        logging.debug("aws:command_id = %s", command_id)

        # We need a little bit of time to wait for a command
        time.sleep(2)

        logging.debug("aws:Waiting command id %s to finish", command_id)
        self.wait_ssm_command_finished(command_id)

        logging.debug("aws:Get command id %s status", command_id)
        command_id_status = self.get_ssm_command_id_status(command_id)
        logging.debug("aws:Command status = %s", command_id_status)

        stdout_key = self.get_s3_ssm_command_id_key(command_id, 'stdout')
        stdout_str = self.get_s3_file_content(stdout_key)
        stderr_str = ''

        if command_id_status != 'Success':
            stderr_key = self.get_s3_ssm_command_id_key(command_id, 'stderr')
            stderr_str = self.get_s3_file_content(stderr_key)

        if return_type == 'all':
            return {
                'CommandId': command_id,
                'CommandIdStatus': command_id_status,
                'CommandList': command_list,
                'StdOut': stdout_str,
                'StdErr': stderr_str
            }
        if return_type == 'command_id':
            return command_id
        raise AttributeError(f"Output type '{return_type}' invalid. See docs.")

    def start_instance(self):
        """
        Start an Instance and wait it to become running and status OK

        More
        ----------
        API Definition
            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.start_instances

        This is a mandatory AVH backend method.
        """
        self._init()
        logging.info("aws:Starting EC2 instance %s", self.instance_id)

        try:
            response = self._ec2_client.start_instances(
                InstanceIds=[
                    self.instance_id,
                ]
            )
        except ClientError as e:
            raise RuntimeError from e

        logging.debug("aws:start_ec2_instance:%s", response)
        self.wait_ec2_running()
        self.wait_ec2_status_ok()

        return self.instance_id

    def stop_instance(self):
        """
        Stop an Instance and wait it becomes stopped.

        More
        ----------
        API Definition
            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.stop_instances

        This is a mandatory AVH backend method.
        """
        self._init()
        logging.info("aws:Stopping EC2 instance %s", self.instance_id)

        try:
            response = self._ec2_client.stop_instances(
                InstanceIds=[
                    self.instance_id
                ]
            )
        except ClientError as e:
            raise RuntimeError from e

        logging.debug("aws:stop_instance:%s", response)
        self.wait_ec2_stopped()

        return self.instance_id

    def wait_ec2_status_ok(self):
        """
        Wait an EC2 instance to have a Status == OK.

        More
        ----------
        API Definition
            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Waiter.InstanceStatusOk
        """
        logging.debug("aws:Waiting until EC2 instance id %s Status Ok...", self.instance_id)

        try:
            waiter = self._ec2_client.get_waiter('instance_status_ok')
            waiter.wait(
                InstanceIds=[
                    self.instance_id
                ]
            )
        except WaiterError as e:
            raise RuntimeError from e

    def wait_ec2_running(self):
        """
        Wait an EC2 instance to be running

        More
        ----------
        API Definition
            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Waiter.InstanceRunning
        """
        logging.debug("aws:Waiting until EC2 instance id %s is running...", self.instance_id)

        try:
            waiter = self._ec2_client.get_waiter('instance_running')
            waiter.wait(
                InstanceIds=[
                    self.instance_id
                ]
            )
        except WaiterError as e:
            raise RuntimeError from e

    def wait_ec2_stopped(self):
        """
        Wait an EC2 instance to stop

        More
        ----------
        API Definition
            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Instance.wait_until_stopped
        """
        logging.debug("aws:Waiting until EC2 instance id %s is stopped...", self.instance_id)
        instance = boto3.resource('ec2').Instance(self.instance_id)
        instance.wait_until_stopped()

    def wait_ec2_terminated(self):
        """
        Wait an EC2 instance to terminate

        More
        ----------
        API Definition
            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Instance.wait_until_terminated
        """
        logging.debug("aws:Waiting until EC2 instance id %s is terminated...", self.instance_id)
        instance = boto3.resource('ec2').Instance(self.instance_id)
        instance.wait_until_terminated()

    def wait_s3_object_exists(self, key, delay=5, max_attempts=120):
        """
        Wait an S3 Object to exists

        Parameters
        ----------
        String
            key (S3 Keypath)
            delay (Retry delay in seconds - Default: 5)
            max_attemps (Max retry - Default: 120)

        More
        ----------
        API Definition
            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Waiter.ObjectExists
        """
        try:
            waiter = self._s3_client.get_waiter('object_exists')
            waiter.wait(
                Bucket=self.s3_bucket_name,
                Key=key,
                WaiterConfig={
                    'Delay': delay,
                    'MaxAttempts': max_attempts
                }
            )
        except WaiterError as e:
            raise RuntimeError from e

    def cleanup(self, state):
        self._init()
        if state in (AvhBackendState.RUNNING, AvhBackendState.INVALID):
            pass
        elif (state == AvhBackendState.STARTED) or self.keep_ec2_instance:
            self.stop_instance()
        else:
            self.terminate_instance()

    def wait_ssm_command_finished(self, command_id, delay=5, max_attempts=120):
        """
        Wait the SSM command to reach a terminal status.
        Parameters
        ----------
        String
            command_id (Command ID)
            delay (Retry delay in seconds - Default: 5)
            max_attemps (Max retry - Default: 120)

        More
        ----------
        API Definition
            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ssm.html#SSM.Waiter.CommandExecuted
        """
        try:
            waiter = self._ssm_client.get_waiter('command_executed')
            waiter.wait(
                CommandId=command_id,
                InstanceId=self.instance_id,
                WaiterConfig={
                    'Delay': delay,
                    'MaxAttempts': max_attempts
                }
            )
        except WaiterError:
            if "Failed" in str(WaiterError):
                logging.error("aws:Failed status found while wainting for command id")

    def terminate_instance(self):
        """
        Terminate an Instance and wait it to terminated.

        More
        ----------
        API Definition
            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.terminate_instances

        This is a mandatory AVH backend method.
        """
        self._init()
        logging.debug('aws:terminate_instance: DryRun=True to test for permission check')
        try:
            self._ec2_client.terminate_instances(
                InstanceIds=[
                    self.instance_id
                ],
                DryRun=True
            )
        except ClientError as e:
            if 'DryRunOperation' not in str(e):
                raise RuntimeError from e

        logging.info('aws:Terminating EC2 instance...')

        try:
            response = self._ec2_client.terminate_instances(
                InstanceIds=[
                    self.instance_id
                ]
            )
        except ClientError as e:
            raise RuntimeError from e

        logging.debug("aws:terminate_instance:%s", response)

        self.wait_ec2_terminated()
        return response

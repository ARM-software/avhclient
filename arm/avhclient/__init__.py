# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Arm Ltd. All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0
#

from importlib import metadata

from .avh_client import AvhClient
from .avh_backend import AvhBackend
from .aws_backend import AwsBackend
from .local_backend import LocalBackend

__author__ = metadata.metadata('arm-avhclient')['Author']
__version__ = metadata.version('arm-avhclient')
__all__ = ['AvhClient', 'AvhBackend', 'AwsBackend', 'LocalBackend']

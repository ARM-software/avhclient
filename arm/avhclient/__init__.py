# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Arm Ltd. All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0
#

from importlib import metadata
from importlib.metadata import PackageNotFoundError

from .avh_client import AvhClient
from .avh_backend import AvhBackend
from .aws_backend import AwsBackend
from .local_backend import LocalBackend

try:
    __author__ = metadata.metadata('arm-avhclient')['Author']
    __version__ = metadata.version('arm-avhclient')
except PackageNotFoundError:
    __author__ = "(unknown)"
    __version__ = "(unknown)"

__all__ = ['__author__', '__version__', 'AvhClient', 'AvhBackend', 'AwsBackend', 'LocalBackend']

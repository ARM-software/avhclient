# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Arm Ltd. All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Dict, Type, List, Union


class AvhBackendState(Enum):
    """Possible AWS EC2 instance states."""
    INVALID = None
    CREATED = 'created'
    STARTED = 'started'
    RUNNING = 'running'

    def __str__(self):
        return self.value


class AvhBackend:
    """Backend interface"""

    @staticmethod
    def find_implementations() -> Dict[str, Type[AvhBackend]]:
        """Find all available backend implementations.

        Returns:
            Mapping with backend names and classes.
        """
        return {cls.name(): cls for cls in AvhBackend.__subclasses__()}

    @staticmethod
    def name() -> str:
        """Return the name this backend shall be published as.

        Returns:
            Unique backend identifier.
        """
        raise NotImplementedError()

    @staticmethod
    def priority() -> int:
        """Return a priority fir this backend.
        The priority defines the order different backend implementations are offered to the user.
        The lower the priority value the higher the backend will be listed.

        Returns:
            Priority for this backend
        """
        raise NotImplementedError()

    def prepare(self, force: bool = False) -> AvhBackendState:
        """Runs required commands to prepare the backend for AVH workload.

        Params:
            force: Force preparation on already prepared backends.

        Returns:
            The BackendState the backend was in before preparation.
         """
        raise NotImplementedError()

    def cleanup(self, state: AvhBackendState):
        """Cleanup the backend.
        The backend is brought back into state before call to prepare.

        Params:
            state: The state returned by prepare
        """
        raise NotImplementedError()

    def upload_workspace(self, filename: Union[str, Path]):
        """Upload the workspace content from the given tarball.

        Params:
            filename: The archived workspace.
        """
        raise NotImplementedError()

    def download_workspace(self, filename: Union[str, Path], globs: List[str] = None):
        """Download the workspace content into given tarball.

        Params:
            filename: The archived workspace.
        """
        raise NotImplementedError()

    def run_commands(self, cmds: List[str]):
        """Execute the given commands on the backend.

        Params:
            cmds - List of command strings
        """
        raise NotImplementedError()

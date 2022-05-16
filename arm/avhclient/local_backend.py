# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Arm Ltd. All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0
#

import logging
import os
import subprocess
import tarfile
from pathlib import Path
from shutil import rmtree

from tempfile import TemporaryDirectory, NamedTemporaryFile, gettempdir
from typing import List, Union

from .avh_backend import AvhBackend, AvhBackendState
from .helper import create_archive


class LocalBackend(AvhBackend):
    """AVH Backend implementation running all action on the local machine."""

    @staticmethod
    def name() -> str:
        """Returns the name identifying this backend."""
        return "local"

    @staticmethod
    def priority() -> int:
        """Returns the priority to order the list of backends."""
        return 50

    @property
    def workid(self) -> str:
        """The work directory ID on the local machine."""
        return self._workid

    @workid.setter
    def workid(self, value: str):
        self._workid = value

    @property
    def workdir(self) -> Path:
        """The working directory on the local machine."""
        if self._workid:
            return Path(gettempdir()).joinpath(f"avhwork-{self._workid}")
        return self._workdir or Path(TemporaryDirectory(prefix="avhwork-").name)

    @workdir.setter
    def workdir(self, value: Path):
        self._workdir = value

    def __init__(self):
        self._workid = ''
        self._workdir = None

    def prepare(self, force: bool = False) -> AvhBackendState:
        if not self.workdir.exists():
            logging.info("Creating %s", self.workdir)
            self.workdir.mkdir()
            return AvhBackendState.CREATED
        return AvhBackendState.RUNNING

    def cleanup(self, state: AvhBackendState):
        logging.info("Cleaning up %s", self.workdir)
        if state == AvhBackendState.CREATED:
            rmtree(self.workdir, ignore_errors=True)

    def upload_workspace(self, filename: Union[str, Path]):
        logging.info("Extracting workspace into %s", self.workdir)
        with tarfile.open(filename, mode='r:bz2') as archive:
            archive.extractall(path=self.workdir)

    def run_commands(self, cmds: List[str]):
        shfile = NamedTemporaryFile(prefix="script-", suffix=".sh", dir=self.workdir, delete=False)
        shfile.close()
        with open(shfile.name, mode="w", encoding='UTF-8', newline='\n') as file:
            file.write("#!/bin/bash\n")
            file.write("set +x\n")
            file.write("\n".join(cmds))
            file.write("\n")

        subprocess.run(["bash", shfile.name], check=False, shell=True, cwd=self.workdir)

        os.remove(shfile.name)

    def download_workspace(self, filename: Union[str, Path], globs: List[str] = None):
        logging.info("Archiving workspace from %s", self.workdir)
        create_archive(filename, self.workdir, globs)

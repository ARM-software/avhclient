# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Arm Ltd. All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0
#

import logging
import os
import tarfile
import yaml

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from .avh_backend import AvhBackend, AvhBackendState
from .helper import create_archive


class AvhSpec:
    def __init__(self, path: Path):
        """AVH spec file

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
        """
        self._path = path

        if not path.exists():
            raise RuntimeError from FileNotFoundError(path)

        with open(path) as file:
            self._spec = yaml.safe_load(file)

    def backend_settings(self, backend: str) -> dict[str, Any]:
        return self._spec.get('backend', dict()).get(backend, dict())

    @property
    def workdir(self) -> Path:
        return self._path.parent.joinpath(self._spec.get('workdir', '.')).resolve()

    @property
    def upload(self) -> list[str]:
        return self._spec.get('upload', ['**/*'])

    @property
    def steps(self) -> list:
        return self._spec.get('steps', [])

    @property
    def download(self) -> list[str]:
        return self._spec.get('download', ['**/*'])


class AvhClient:
    @staticmethod
    def get_available_backends() -> list[str]:
        backends = AvhBackend.find_implementations()
        return sorted(backends.keys(), key=lambda k: backends[k].priority())

    def __init__(self, backend):
        self.backend_desc = backend.lower()
        logging.info(f"avh:{self.backend_desc} backend selected!")
        self._set_backend()

    def _set_backend(self):
        backends = AvhBackend.find_implementations()
        if self.backend_desc in backends:
            self.backend = backends[self.backend_desc]()
        else:
            logging.error(f"{self.backend_desc} not supported!")
            raise RuntimeError()

    def prepare(self) -> AvhBackendState:
        """Prepare the backend to execute AVH workload."""
        return self.backend.prepare()

    def upload(self, workspace: Path = Path(""), patterns: list[str] = ['**/*']):
        """Upload the workspace to the AVH backend

        Args:
            workspace: The base directory for the workspace
            patterns: List if glob patters. Patterns prefixed with -: denote excludes.
        """
        avhin = None
        try:
            avhin = NamedTemporaryFile(mode='w+b', prefix='avhin-', suffix='.tbz2', delete=False)
            avhin.close()
            create_archive(avhin.name, workspace, patterns, verbose=True)
            self.backend.upload_workspace(avhin.name)
        finally:
            if avhin:
                os.remove(avhin.name)

    def run(self, cmds: list[str]):
        """Run given commands on AVH backend

        Args:
            cmds: List of commands to run.
        """
        self.backend.run_commands(cmds)

    def download(self, workspace: Path = Path(""), patterns: list[str] = ['**/*']):
        """Download the workspace from the AVH backend

        Args:
            workspace: The base directory for the workspace
            patterns: List if glob patters. Patterns prefixed with -: denote excludes.
        """
        avhout = None
        try:
            avhout = NamedTemporaryFile(mode='r+b', prefix='avhout-', suffix='.tbz2', delete=False)
            avhout.close()
            self.backend.download_workspace(avhout.name, patterns)
            with tarfile.open(avhout.name, mode='r:bz2') as archive:
                archive.list(verbose=False)
                archive.extractall(path=workspace)
        finally:
            if avhout:
                os.remove(avhout.name)

    def cleanup(self, state: AvhBackendState = AvhBackendState.CREATED):
        """Cleanup backend into a former state.

        Args:
            state: The state to turn backend into.
        """
        self.backend.cleanup(state)

    def execute(self, specfile: Path = Path("./avh.yml")):
        """Execute the AVH job specified by given specfile.

        Args:
            specfile: Path to the YAML specfile.
        """
        backend_state = AvhBackendState.INVALID

        spec = AvhSpec(specfile)
        for k, v in spec.backend_settings(self.backend.name()).items():
            kk = k.replace('-', '_')
            if hasattr(self.backend, kk):
                setattr(self.backend, kk, v)

        try:
            logging.info("Preparing instance...")
            backend_state = self.backend.prepare()

            logging.info("Uploading workspace...")
            self.upload(spec.workdir, spec.upload)

            logging.info("Executing...")
            for step in spec.steps:
                if 'run' in step:
                    cmds = [cmd for cmd in step['run'].split('\n') if cmd]
                    self.run(cmds)

            logging.info("Downloading workspace...")
            self.download(spec.workdir, spec.download)
        finally:
            self.backend.cleanup(backend_state)

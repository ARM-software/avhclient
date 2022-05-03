# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Arm Ltd. All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0
#

import logging
import os
import tarfile

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, List

import yaml

from .avh_backend import AvhBackend, AvhBackendState
from .helper import create_archive


class AvhSpec:
    """Wrapper for AVH spec file."""

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
            download: (optional) List of glob patterns of files to be retrieved back from the AVH backend.
               (see glob format)

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

        with open(path, encoding='UTF-8') as file:
            self._spec = yaml.safe_load(file)

    def backend_settings(self, backend: str) -> Dict[str, Any]:
        """Get the backend specific settings.

        Params:
            backend: The backend name to get settings for.

        Returns:
            The mapping of settings for the given backend.
        """
        return self._spec.get('backend', {}).get(backend, {})

    @property
    def workdir(self) -> Path:
        """The working directory within the local workspace."""
        return self._path.parent.joinpath(self._spec.get('workdir', '.')).resolve()

    @property
    def upload(self) -> List[str]:
        """The glob pattern for files to be uploaded to the backend."""
        return self._spec.get('upload', ['**/*'])

    @property
    def steps(self) -> List:
        """The steps to be executed on the backend."""
        return self._spec.get('steps', [])

    @property
    def download(self) -> List[str]:
        """The glob pattern for files to be downloaded from the backend."""
        return self._spec.get('download', ['**/*'])


class AvhClient:
    """AVH Client"""

    @staticmethod
    def get_available_backends() -> List[str]:
        """Get a list of available backend implementations.

        Returns:
            List of backend names sorted by priority.
        """
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

    def prepare(self, force: bool = False) -> AvhBackendState:
        """Prepare the backend to execute AVH workload.

        Args:
            force: Force (re)preparation of the backend.

        Returns:
            The BackendState the backend was in before preparation.
        """
        return self.backend.prepare()

    def upload(self, workspace: Path = Path(""), patterns: List[str] = None):
        """Upload the workspace to the AVH backend

        Args:
            workspace: The base directory for the workspace
            patterns: List if glob patters. Patterns prefixed with -: denote excludes.
        """
        if not patterns:
            patterns = ['**/*']
        avhin = None
        try:
            avhin = NamedTemporaryFile(mode='w+b', prefix='avhin-', suffix='.tbz2', delete=False)
            avhin.close()
            create_archive(avhin.name, workspace, patterns, verbose=True)
            self.backend.upload_workspace(avhin.name)
        finally:
            if avhin:
                os.remove(avhin.name)

    def run(self, cmds: List[str]):
        """Run given commands on AVH backend

        Args:
            cmds: List of commands to run.
        """
        self.backend.run_commands(cmds)

    def download(self, workspace: Path = Path(""), patterns: List[str] = None):
        """Download the workspace from the AVH backend

        Args:
            workspace: The base directory for the workspace
            patterns: List if glob patters. Patterns prefixed with -: denote excludes.
        """
        if not patterns:
            patterns = ['**/*']
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
        for key, value in spec.backend_settings(self.backend.name()).items():
            kkey = key.replace('-', '_')
            if hasattr(self.backend, kkey):
                setattr(self.backend, kkey, value)

        try:
            logging.info("")
            logging.info("Preparing instance...")
            logging.info('='*80)
            backend_state = self.backend.prepare()

            logging.info("")
            logging.info("Uploading workspace...")
            logging.info('='*80)
            self.upload(spec.workdir, spec.upload)

            logging.info("")
            logging.info("Executing...")
            logging.info('='*80)
            for step in spec.steps:
                if 'run' in step:
                    cmds = [cmd for cmd in step['run'].split('\n') if cmd]
                    self.run(cmds)

            logging.info("")
            logging.info("Downloading workspace...")
            logging.info('='*80)
            self.download(spec.workdir, spec.download)
        finally:
            logging.info("")
            logging.info("Teardown instance...")
            logging.info('='*80)
            self.backend.cleanup(backend_state)

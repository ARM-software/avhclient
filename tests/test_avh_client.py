# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Arm Ltd. All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0
#

import tarfile

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Union
from unittest import TestCase
from unittest.mock import MagicMock, patch, Mock, PropertyMock, call

from arm.avhclient import AvhClient, AvhBackend
from arm.avhclient.avh_backend import AvhBackendState
from arm.avhclient.helper import create_archive


class MockBackend(AvhBackend):
    @staticmethod
    def name() -> str:
        return "mock"

    @staticmethod
    def priority() -> int:
        return 10

    def __init__(self):
        self.mock = MagicMock(self)
        self.uploaded = []
        self._mock_setting = ""

    def record_uploaded(self, filename):
        with tarfile.open(filename, mode='r:bz2') as archive:
            self.uploaded = archive.getnames()

    def prepare(self, force: bool = False) -> AvhBackendState:
        return self.mock.prepare(force)

    def cleanup(self, state: AvhBackendState):
        self.mock.cleanup(state)

    def upload_workspace(self, filename: Union[str, Path]):
        self.mock.upload_workspace(filename)

    def download_workspace(self, filename: Union[str, Path], globs: List[str] = None):
        self.mock.download_workspace(filename, globs)

    def run_commands(self, cmds: List[str]):
        self.mock.run_commands(cmds)


class TestAvhClient(TestCase):
    def test_upload(self):
        # GIVEN a AvhClient with mock'ed backend
        client = AvhClient("mock")
        # ... AND record upload_workspace archive content
        client.backend.mock.upload_workspace = MagicMock(side_effect=lambda f: client.backend.record_uploaded(f))
        # WHEN running upload action on this file's folder with some glob pattern
        this_file = Path(__file__)
        client.upload(this_file.parent, ["**/*.py", "-:_*"])

        # THEN the backend upload_workspace method got called once
        client.backend.mock.upload_workspace.assert_called_once()
        # ... AND the uploaded temporary archive got removed again
        self.assertFalse(Path(client.backend.mock.upload_workspace.call_args.args[0]).exists())
        # ... AND the archive contains files matching the given glob pattern
        self.assertIn(this_file.name, client.backend.uploaded)
        self.assertNotIn("__init__.py", client.backend.uploaded)

    def test_upload_failure(self):
        # GIVEN a AvhClient with mock'ed backend
        client = AvhClient("mock")
        # ... AND the upload_workspace method raising a RuntimeError
        client.backend.mock.upload_workspace = MagicMock(side_effect=RuntimeError)

        # WHEN running upload action on this file's folder with some glob pattern
        this_file = Path(__file__)
        with self.assertRaises(RuntimeError):
            client.upload(this_file.parent, ["**/*.py", "-:_*"])

        # THEN the backend upload_workspace method got called once
        client.backend.mock.upload_workspace.assert_called_once()
        # ... AND the uploaded temporary archive got removed again
        self.assertFalse(Path(client.backend.mock.upload_workspace.call_args.args[0]).exists())

    def test_upload_notemp(self):
        # GIVEN a AvhClient with mock'ed backend
        client = AvhClient("mock")
        # ... AND the NamedTemporaryFile method raising a RuntimeError
        with patch("arm.avhclient.avh_client.NamedTemporaryFile") as mock:
            mock.side_effect = RuntimeError

            # WHEN running upload action on this file's folder with some glob pattern
            this_file = Path(__file__)
            with self.assertRaises(RuntimeError):
                client.upload(this_file.parent, ["**/*.py", "-:_*"])

        # THEN the backend upload_workspace method got not called
        client.backend.mock.upload_workspace.assert_not_called()

    def test_download(self):
        # GIVEN a AvhClient with mock'ed backend
        client = AvhClient("mock")
        this_file = Path(__file__)
        client.backend.mock.download_workspace = \
            MagicMock(side_effect=lambda f, g: create_archive(f, this_file.parent, g))

        # WHEN running download action to a temporary directory
        with TemporaryDirectory() as temp_dir:
            client.download(temp_dir, ["**/*.py", "-:_*"])

            # THEN the backend download_workspace method got called once
            client.backend.mock.download_workspace.assert_called_once()
            # ... AND the downloaded temporary archive got removed again
            self.assertFalse(Path(client.backend.mock.download_workspace.call_args.args[0]).exists())
            # ... AND the expected files are present
            self.assertTrue(Path(temp_dir).joinpath(this_file.name).exists())
            self.assertFalse(Path(temp_dir).joinpath("__init__.py").exists())

    def test_download_failure(self):
        # GIVEN a AvhClient with mock'ed backend
        client = AvhClient("mock")
        # ... AND the download_workspace method raising a RuntimeError
        client.backend.mock.download_workspace = MagicMock(side_effect=RuntimeError)

        # WHEN running download action to a temporary directory
        with TemporaryDirectory() as temp_dir:
            with self.assertRaises(RuntimeError):
                client.download(temp_dir, ["**/*.py", "-:_*"])

            # THEN the backend download_workspace method got called once
            client.backend.mock.download_workspace.assert_called_once()
            # ... AND the downloaded temporary archive got removed again
            self.assertFalse(Path(client.backend.mock.download_workspace.call_args.args[0]).exists())
            # ... AND the temporary directory is still empty
            self.assertFalse(any(Path(temp_dir).iterdir()))

    def test_download_notemp(self):
        # GIVEN a AvhClient with mock'ed backend
        client = AvhClient("mock")
        # ... AND the NamedTemporaryFile method raising a RuntimeError
        with patch("arm.avhclient.avh_client.NamedTemporaryFile") as mock:
            mock.side_effect = RuntimeError

            # WHEN running download action to a temporary directory
            with TemporaryDirectory() as temp_dir:
                with self.assertRaises(RuntimeError):
                    client.download(temp_dir, ["**/*.py", "-:_*"])

                # THEN the backend download_workspace method got not called
                client.backend.mock.download_workspace.assert_not_called()
                # ... AND the temporary directory is still empty
                self.assertFalse(any(Path(temp_dir).iterdir()))

    def test_execute(self):
        # GIVEN a AvhClient with mock'ed backend
        client = AvhClient("mock")
        # ... AND mock-setting property
        client.backend.mock_setting = "setting"
        # ... AND mocked backend state returned on prepare
        backend_state_mock = Mock()
        client.backend.mock.prepare = Mock(return_value=backend_state_mock)
        # ... AND a mocked spec, upload and download methods
        with patch("arm.avhclient.avh_client.AvhSpec") as spec_mock, \
                patch("arm.avhclient.avh_client.AvhClient.upload"), \
                patch("arm.avhclient.avh_client.AvhClient.download"):
            type(spec_mock.return_value).backend_settings = MagicMock(return_value={'mock-setting': 'mocked'})
            type(spec_mock.return_value).workdir = Mock()
            type(spec_mock.return_value).upload = Mock()
            type(spec_mock.return_value).steps = PropertyMock(return_value=[{'run': 'cmdA\ncmdB'}, {'run': 'cmdC'}])
            type(spec_mock.return_value).download = Mock()

            # WHEN calling execute
            client.execute()

            # THEN the mock-setting as been set to 'mocked'
            self.assertEqual(client.backend.mock_setting, "mocked")
            # ... AND prepare was called
            client.backend.mock.prepare.assert_called_once()
            # ... AND upload_workspace was called
            client.upload.assert_called_with(type(spec_mock.return_value).workdir,
                                             type(spec_mock.return_value).upload)
            # ... AND run was called with all run commands
            client.backend.mock.run_commands.assert_has_calls([
                call(["cmdA", "cmdB"]),
                call(["cmdC"])
            ])
            # ... AND download_workspace was called
            client.download.assert_called_with(type(spec_mock.return_value).workdir,
                                               type(spec_mock.return_value).download)
            # ... AND cleanup was called
            client.backend.mock.cleanup.assert_called_with(backend_state_mock)

    def test_execute_prepare_failure(self):
        # GIVEN a AvhClient with mock'ed backend
        client = AvhClient("mock")
        # ... AND backend raise exception on prepare
        client.backend.mock.prepare = Mock(side_effect=RuntimeError)
        # ... AND a mocked spec, upload and download methods
        with patch("arm.avhclient.avh_client.AvhSpec") as spec_mock, \
                patch("arm.avhclient.avh_client.AvhClient.upload"), \
                patch("arm.avhclient.avh_client.AvhClient.download"):
            type(spec_mock.return_value).backend_settings = MagicMock(return_value={})
            type(spec_mock.return_value).workdir = Mock()
            type(spec_mock.return_value).upload = Mock()
            type(spec_mock.return_value).steps = PropertyMock(return_value=[{'run': 'cmdA\ncmdB'}, {'run': 'cmdC'}])
            type(spec_mock.return_value).download = Mock()

            # WHEN calling execute
            with self.assertRaises(RuntimeError):
                client.execute()

            # THEN prepare was called
            client.backend.mock.prepare.assert_called_once()
            # ... AND upload_workspace was not called
            client.upload.assert_not_called()
            # ... AND run was not called
            client.backend.mock.run_commands.assert_not_called()
            # ... AND download_workspace was not called
            client.download.assert_not_called()
            # ... AND cleanup was called with invalid state
            client.backend.mock.cleanup.assert_called_with(AvhBackendState.INVALID)

    def test_execute_upload_failure(self):
        # GIVEN a AvhClient with mock'ed backend
        client = AvhClient("mock")
        # ... AND mocked backend state returned on prepare
        backend_state_mock = Mock()
        client.backend.mock.prepare = Mock(return_value=backend_state_mock)
        # ... AND a mocked spec, upload and download methods
        with patch("arm.avhclient.avh_client.AvhSpec") as spec_mock, \
                patch("arm.avhclient.avh_client.AvhClient.upload") as upload_mock, \
                patch("arm.avhclient.avh_client.AvhClient.download"):
            type(spec_mock.return_value).backend_settings = MagicMock(return_value={})
            type(spec_mock.return_value).workdir = Mock()
            type(spec_mock.return_value).upload = Mock()
            type(spec_mock.return_value).steps = PropertyMock(return_value=[{'run': 'cmdA\ncmdB'}, {'run': 'cmdC'}])
            type(spec_mock.return_value).download = Mock()
            # AND ... upload raising an exception
            upload_mock.side_effect = RuntimeError

            # WHEN calling execute
            with self.assertRaises(RuntimeError):
                client.execute()

            # THEN prepare was called
            client.backend.mock.prepare.assert_called_once()
            # ... AND upload_workspace was called
            client.upload.assert_called_with(type(spec_mock.return_value).workdir,
                                             type(spec_mock.return_value).upload)
            # ... AND run was not called
            client.backend.mock.run_commands.assert_not_called()
            # ... AND download_workspace was not called
            client.download.assert_not_called()
            # ... AND cleanup was called
            client.backend.mock.cleanup.assert_called_with(backend_state_mock)

# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Arm Ltd. All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0
#
import os
import tarfile
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest import TestCase

from arm.avhclient.helper import _iglob, create_archive


class TestHelper(TestCase):
    def test_iglob(self):
        this_file = Path(__file__)
        py_files = _iglob("**/*.py", this_file.parent.parent)
        self.assertIn(this_file, list(py_files))

    def test_create_archive(self):
        this_file = Path(__file__)

        archive_file = NamedTemporaryFile(mode='w+b', suffix='.tbz2', delete=False)
        archive_file.close()
        self.addCleanup(lambda: os.remove(archive_file.name))

        create_archive(archive_file.name, this_file.parent, ["*.py", "-:_*"], verbose=True)

        with tarfile.open(archive_file.name, mode='r:bz2') as archive:
            self.assertIn(this_file.name, archive.getnames())
            self.assertNotIn("__init__.py", archive.getnames())

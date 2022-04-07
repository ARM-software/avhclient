# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Arm Ltd. All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0
#

import tarfile
from glob import iglob

from pathlib import Path
from typing import Union, List, Iterable


def _iglob(pathname: Union[str, Path], root_dir: Union[str, Path] = Path.cwd(),
           recursive: bool = True, files_only: bool = True) -> Iterable[Path]:
    """Wrapper for glob.iglob

    Args:
        pathname: A glob pattern to evaluate relative to root_dir.
        root_dir: The base directory to evaluate pattern from, defaults to cwd.
        recursive: Make ** matching subdirectories, default to true.
        files_only: Returns only normal files

    Returns:
        Generator listing all match results.
    """
    if not isinstance(root_dir, Path):
        root_dir = Path(root_dir)
    pathname = root_dir.joinpath(pathname)
    for match in iglob(str(pathname), recursive=recursive):
        match = Path(match)
        if not files_only or match.is_file():
            yield match


def create_archive(filename: Union[str, Path],
                   root_dir: Union[str, Path] = Path.cwd(),
                   globs: List[str] = None,
                   verbose: bool = False):
    """Create an bzip2-compressed tarball of the given directory.

    Files matching the given glob patterns underneath root_dir are archived. The patterns
    are applied in order. Patterns without prefix denote includes. A pattern prefixed with
    `-:` denotes an exclude and removes all matching files that have been included previously.

    Args:
        filename: The filename of the resulting archive.
        root_dir: The root directory for the archive, defaults to current working directory.
        globs: A list of glob filters with includes and excludes, defaults to **/*.
        verbose: List archive content if set to True.
    """
    if not isinstance(root_dir, Path):
        root_dir = Path(root_dir)
    if not globs:
        globs = ["**/*"]

    with tarfile.open(filename, mode='w:bz2') as archive:
        files = set()
        for pattern in globs:
            if pattern.startswith('-:'):
                files = files - set(_iglob(pattern[2:], root_dir=root_dir))
            else:
                files.update(set(_iglob(pattern, root_dir=root_dir)))
        for file in files:
            archive.add(file, arcname=file.relative_to(root_dir))
        if verbose:
            archive.list(verbose=False)

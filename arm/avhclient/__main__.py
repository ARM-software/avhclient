# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Arm Ltd. All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0
#

import signal
import sys

from .avh_cli import AvhCli


def main():
    # Register a minimal signal handler to SIGTERM to be notified.
    # This allows to gracefully cleanup resources on such an event.
    signal.signal(signal.SIGTERM, lambda *args: sys.exit(0))

    AvhCli()


if __name__ == "__main__":
    main()

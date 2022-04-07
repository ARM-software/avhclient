# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Arm Ltd. All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0
#

import inspect
import logging
import re
import sys

from argparse import ArgumentParser, SUPPRESS, Namespace
from enum import Enum
from gettext import gettext as _
from inspect import signature, Signature
from itertools import islice
from types import FunctionType

from typing import _GenericAlias as GenericAlias

from arm.avhclient import AvhClient, AvhBackend, __version__


class AvhCli:
    """Arm Virtual Hardware Command Line Interface"""

    def __init__(self):
        parser = self._parser()

        args = parser.parse_known_args()[0]
        if args.verbosity:
            verbosity = args.verbosity
            logging.basicConfig(format='[%(levelname)s]\t%(message)s', level=verbosity)
            logging.debug("Verbosity level is set to %s", verbosity)

        avh_client = AvhClient(args.backend)

        self._add_commands(parser)
        self._add_backend_args(parser, avh_client.backend)

        args = parser.parse_args()

        self._consume_backend_args(avh_client.backend, args)

        func = AvhClient.__dict__[args.subcmd.replace('-', '_')]
        params = signature(func).parameters
        func_args = [vars(args)[param.replace('-', '_')] for param in islice(params.keys(), 1, None)]
        try:
            func(avh_client, *func_args)
        except RuntimeError as e:
            if e.__cause__ is not None:
                logging.error(e.__cause__.__doc__)
                logging.error(e.__cause__)
            if str(e):
                logging.error(e)
            sys.exit(1)
        sys.exit(0)

    @staticmethod
    def _parser() -> ArgumentParser:
        parser = ArgumentParser(add_help=False)

        parser.add_argument('-v', '--verbosity',
                            type=str,
                            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                            default='INFO',
                            help='Set the output verbosity. Default: INFO')

        parser.add_argument('-b', '--backend',
                            type=str,
                            choices=AvhClient.get_available_backends(),
                            default='aws',
                            help=f'Select AVH backend to use. Default: {AvhClient.get_available_backends()[0]}')

        parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')

        return parser

    @staticmethod
    def _add_argument(parser, argname: str, argtype: type = str, default=None, helptext: str = ''):
        kwargs = {'help': helptext, 'required': default is None}
        if argtype is bool:
            kwargs['action'] = 'store_true'
        elif isinstance(argtype, GenericAlias):
            if argtype.__origin__ is list:
                kwargs['type'] = argtype.__args__[0] if len(argtype.__args__) > 0 else str
                kwargs['nargs'] = '+' if default is None else '*'
        elif issubclass(argtype, Enum):
            kwargs['choices'] = list(filter(lambda v: v.value, argtype))
            kwargs['type'] = type(kwargs['choices'][0])
        else:
            kwargs['type'] = argtype
        if default is not None:
            kwargs['default'] = default
            if not kwargs['help'].endswith('\n'):
                kwargs['help'] += '\n'
            kwargs['help'] += f"Defaults to '{default}'."
        parser.add_argument(f"--{argname.replace('_', '-')}", **kwargs)

    @staticmethod
    def _add_backend_args(parser: ArgumentParser, backend: AvhBackend):
        group = parser.add_argument_group(f"{backend.name()} backend properties")
        for key, value in filter(lambda m: not m[0].startswith('_') and isinstance(m[1], property),
                           backend.__class__.__dict__.items()):
            sig = inspect.signature(value.fget)
            AvhCli._add_argument(group, key, sig.return_annotation, getattr(backend, key), value.__doc__)

    @staticmethod
    def _consume_backend_args(backend: AvhBackend, args: Namespace):
        args = vars(args)
        for key, _ in filter(lambda m: not m[0].startswith('_') and isinstance(m[1], property),
                           backend.__class__.__dict__.items()):
            if key in args:
                setattr(backend, key, args[key])

    @staticmethod
    def _add_commands(parser: ArgumentParser):
        parser.add_argument('-h', '--help', action='help',
                            default=SUPPRESS, help=_('show this help message and exit'))

        subparsers = parser.add_subparsers(dest='subcmd', required=True, help='sub-command help')

        for name, member in AvhClient.__dict__.items():
            if isinstance(member, FunctionType) and not name.startswith('_'):
                func_help = member.__doc__.split('\n')[0] if member.__doc__ else ''
                subparser = subparsers.add_parser(name.replace('_', '-'), help=func_help)
                params = signature(member).parameters
                for param in islice(params.items(), 1, None):
                    param_help = re.search(f"{param[0]}: (.*)", member.__doc__) if member.__doc__ else None
                    param_help = param_help.group(1) if param_help else ""
                    param_type = param[1].annotation if param[1].annotation != Signature.empty else str
                    param_default = param[1].default if param[1].default != Signature.empty else None
                    AvhCli._add_argument(subparser, param[0], param_type, param_default, param_help)

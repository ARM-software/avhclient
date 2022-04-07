# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Arm Ltd. All rights reserved.
#
# SPDX-License-Identifier: Apache-2.0
#

import contextlib
from enum import Enum

from io import StringIO
from typing import List
from unittest import TestCase
from unittest.mock import patch, MagicMock

from arm.avhclient.avh_cli import AvhCli


class TestAvhCli(TestCase):

    def test_parser_version(self):
        parser = AvhCli._parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(['--version'])

    def test_parser_verbosity(self):
        parser = AvhCli._parser()
        args = parser.parse_args(['--verbosity', 'DEBUG'])
        self.assertEqual(args.verbosity, 'DEBUG')

    def test_parser_backend(self):
        with patch('arm.avhclient.avh_cli.AvhClient.get_available_backends') as mock:
            mock.return_value = ['backend1', 'backend2']
            parser = AvhCli._parser()

        args = parser.parse_args(['--backend', 'backend1'])
        self.assertEqual(args.backend, 'backend1')

    def test_parser_backend_invalid(self):
        with patch('arm.avhclient.avh_cli.AvhClient.get_available_backends') as mock:
            mock.return_value = ['backend1', 'backend2']
            parser = AvhCli._parser()

        with self.assertRaises(SystemExit):
            parser.parse_args(['--backend', 'backend3'])

    def test_add_commands_without_param(self):
        parser = AvhCli._parser()
        cmd_mock = MagicMock()

        def cmd1(s):
            """Command A description"""
            cmd_mock()

        def cmd2(s):
            """Command B description"""
            cmd_mock()

        with patch('arm.avhclient.avh_cli.AvhClient') as mock:
            mock.cmdA = cmd1
            mock.cmdB = cmd2
            AvhCli._add_commands(parser)

        help_str = parser.format_help()

        self.assertRegex(help_str, "\\{cmdA,cmdB\\}")
        self.assertRegex(help_str, "cmdA\\s+Command A description")
        self.assertRegex(help_str, "cmdB\\s+Command B description")

    def test_add_commands_with_str_param(self):
        parser = AvhCli._parser()
        cmd_mock = MagicMock()

        def cmd1(s, str_param: str):
            """Command A description

            Params:
                str_param: A mandatory string argument.
            """
            cmd_mock()

        with patch('arm.avhclient.avh_cli.AvhClient') as mock:
            mock.cmdA = cmd1
            AvhCli._add_commands(parser)

        help_io = StringIO()
        with self.assertRaises(SystemExit), contextlib.redirect_stdout(help_io):
            parser.parse_args(['cmdA', '--help'])

        help_str = help_io.getvalue()
        self.assertRegex(help_str, "usage:.*cmdA.*[^\\[]--str-param STR_PARAM[^\\]]")
        self.assertRegex(help_str, "--str-param STR_PARAM\\s+A mandatory string argument.")

    def test_add_commands_with_opt_str_param(self):
        parser = AvhCli._parser()
        cmd_mock = MagicMock()

        def cmd1(s, str_param: str = "default"):
            """Command A description

            Params:
                str_param: An optional string argument.
            """
            cmd_mock()

        with patch('arm.avhclient.avh_cli.AvhClient') as mock:
            mock.cmdA = cmd1
            AvhCli._add_commands(parser)

        help_io = StringIO()
        with self.assertRaises(SystemExit), contextlib.redirect_stdout(help_io):
            parser.parse_args(['cmdA', '--help'])

        help_str = help_io.getvalue()
        self.assertRegex(help_str, "usage:.*cmdA.*\\[--str-param STR_PARAM\\]")
        self.assertRegex(help_str, "--str-param STR_PARAM\\s+An optional string argument. Defaults to 'default'.")

    def test_add_commands_with_list_str_param(self):
        parser = AvhCli._parser()
        cmd_mock = MagicMock()

        def cmd1(s, str_param: List[str]):
            """Command A description

            Params:
                str_param: A mandatory string argument.
            """
            cmd_mock()

        with patch('arm.avhclient.avh_cli.AvhClient') as mock:
            mock.cmdA = cmd1
            AvhCli._add_commands(parser)

        help_io = StringIO()
        with self.assertRaises(SystemExit), contextlib.redirect_stdout(help_io):
            parser.parse_args(['cmdA', '--help'])

        help_str = help_io.getvalue()
        self.assertRegex(help_str, "usage:.*cmdA.*--str-param STR_PARAM \\[STR_PARAM ...\\]")
        self.assertRegex(help_str, "--str-param STR_PARAM \\[STR_PARAM ...\\]\\s+A mandatory string argument.")

    def test_add_commands_with_opt_list_str_param(self):
        parser = AvhCli._parser()
        cmd_mock = MagicMock()

        def cmd1(s, str_param: List[str] = ['default']):
            """Command A description

            Params:
                str_param: An optional string argument.
            """
            cmd_mock()

        with patch('arm.avhclient.avh_cli.AvhClient') as mock:
            mock.cmdA = cmd1
            AvhCli._add_commands(parser)

        args = parser.parse_args(['cmdA', '--str-param', 'valA', 'valB'])
        self.assertSequenceEqual(args.str_param, ['valA', 'valB'])

    def test_add_commands_with_bool_param(self):
        parser = AvhCli._parser()
        cmd_mock = MagicMock()

        def cmd1(s, bool_param: bool):
            """Command A description

            Params:
                bool_param: A boolean argument.
            """
            cmd_mock()

        with patch('arm.avhclient.avh_cli.AvhClient') as mock:
            mock.cmdA = cmd1
            AvhCli._add_commands(parser)

        help_io = StringIO()
        with self.assertRaises(SystemExit), contextlib.redirect_stdout(help_io):
            parser.parse_args(['cmdA', '--help'])

        help_str = help_io.getvalue()
        self.assertRegex(help_str, "usage:.*cmdA.*--bool-param")
        self.assertRegex(help_str, "--bool-param\\s+A boolean argument.")

    def test_add_commands_with_enum_param(self):
        parser = AvhCli._parser()
        cmd_mock = MagicMock()

        class ParamEnum(Enum):
            VALUE1 = 'value1'
            VALUE2 = 'value2'
            VALUE3 = 'value3'

            def __str__(self):
                return self.value

        def cmd1(s, enum_param: ParamEnum):
            """Command A description

            Params:
                enum_param: An enum argument.
            """
            cmd_mock()

        with patch('arm.avhclient.avh_cli.AvhClient') as mock:
            mock.cmdA = cmd1
            AvhCli._add_commands(parser)

        help_io = StringIO()
        with self.assertRaises(SystemExit), contextlib.redirect_stdout(help_io):
            parser.parse_args(['cmdA', '--help'])

        help_str = help_io.getvalue()
        self.assertRegex(help_str, "usage:.*cmdA.*--enum-param \\{value1,value2,value3\\}")
        self.assertRegex(help_str, "--enum-param \\{value1,value2,value3\\}\\s+An enum argument.")

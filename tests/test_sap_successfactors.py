# -*- coding: utf-8 -*-
"""
Tests for the `sap_success_factors` package.
"""

from __future__ import absolute_import, unicode_literals, with_statement

import unittest

import ddt
import mock
from integrated_channels.sap_success_factors.utils import current_time_is_in_interval, parse_language_code
from pytest import raises

from enterprise.lms_api import parse_lms_api_datetime


@ddt.ddt
class TestSapSuccessFactorsUtils(unittest.TestCase):
    """
    Test the individual functions used by the SAPSuccessFactors course transformation.
    """

    @ddt.data(
        ('cy', 'Welsh'),
        ('en-us', 'English'),
        ('zh-hk', 'Chinese Hong Kong'),
        ('ru-faaaaaake', 'Russian'),
        ('not-real', 'English')
    )
    @ddt.unpack
    def test_parse_language_code_valid(self, code, expected):
        assert parse_language_code(code) == expected

    def test_unparsable_language_code(self):
        with raises(ValueError) as exc_info:
            parse_language_code('this-is-incomprehensible')
        assert str(exc_info.value) == (
            'Language codes may only have up to two components. Could not parse: this-is-incomprehensible'
        )

    @ddt.data(
        ('2011-01-01T00:00:00Z', '2011-01-01T00:00:00Z', False),
        ('2015-01-01T00:00:00Z', '2017-01-01T00:00:00Z', True),
        ('2018-01-01T00:00:00Z', '2020-01-01T00:00:00Z', False),
    )
    @ddt.unpack
    @mock.patch('integrated_channels.sap_success_factors.utils.timezone')
    def test_current_time_in_interval(self, start, end, expected, fake_timezone):
        fake_timezone.now.return_value = parse_lms_api_datetime('2016-01-01T00:00:00Z')
        assert current_time_is_in_interval(start, end) is expected

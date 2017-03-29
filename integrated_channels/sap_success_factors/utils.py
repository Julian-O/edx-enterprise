"""
Utilities for Enterprise Integrated Channel SAP SuccessFactors.
"""
from __future__ import absolute_import, unicode_literals

import datetime
import json

from django.apps import apps
from django.utils import timezone

from enterprise.lms_api import parse_lms_api_datetime
from integrated_channels.integrated_channel.course_metadata import BaseCourseExporter


UNIX_EPOCH = datetime.datetime(1970, 1, 1, tzinfo=timezone.utc)
UNIX_MIN_DATE_STRING = '1970-01-01T00:00:00Z'
UNIX_MAX_DATE_STRING = '2038-01-19T03:14:07Z'


class SapCourseExporter(BaseCourseExporter):
    """
    Class to provide data transforms for SAP SuccessFactors course export task.
    """

    STATUS_ACTIVE = 'ACTIVE'
    STATUS_INACTIVE = 'INACTIVE'

    def __init__(self, user, plugin_configuration):
        self.removed_courses_resolved = False
        super(SapCourseExporter, self).__init__(user, plugin_configuration)

    def get_serialized_data(self):
        final_structure = {
            'ocnCourses': self.courses
        }
        return json.dumps(final_structure, sort_keys=True).encode('utf-8')

    def resolve_removed_courses(self, previous_audit_summary):
        """
        Ensures courses that are no longer in the catalog get properly marked as inactive.

        Args:
            previous_audit_summary (dict): The previous audit summary from the last course export.

        Returns:
            An audit summary of courses with information about their presence in the catalog and current status.
        """
        if self.removed_courses_resolved:
            return {}

        new_audit_summary = {}

        for course in self.courses:
            key = course['courseID']
            status = course['status']
            new_audit_summary[key] = {
                'in_catalog': True,
                'status': status,
            }
            # Remove the key from previous audit summary so we can process courses that are no longer present.
            if key in previous_audit_summary:
                del previous_audit_summary[key]

        for key, summary in previous_audit_summary:
            new_audit_summary[key] = {
                'in_catalog': False,
                'status': self.STATUS_INACTIVE,
            }

            # Add a course payload to self.courses so that courses no longer in the catalog are marked inactive.
            if summary['status'] == self.STATUS_ACTIVE and summary['in_catalog']:
                self.courses.append({
                    'courseID': key,
                    'status': self.STATUS_INACTIVE,
                })

        self.removed_courses_resolved = True
        return new_audit_summary

    data_transform = {
        'courseID': lambda x: x['key'],
        'providerID': lambda x: apps.get_model(
            'sap_success_factors',
            'SAPSuccessFactorsGlobalConfiguration'
        ).current().provider_id,
        'status': lambda x: (SapCourseExporter.STATUS_ACTIVE if x['availability'] == 'Current'
                             else SapCourseExporter.STATUS_INACTIVE),
        'title': lambda x: [
            {
                'locale': 'English',
                'value': x['title']
            },
        ],
        'description': lambda x: [
            {
                'locale': 'English',
                'value': x['full_description'] or x['short_description'] or '',
            },
        ],
        'thumbnailURI': lambda x: (x['image']['src'] or ''),
        'content': lambda x: [
            {
                'providerID': apps.get_model(
                    'sap_success_factors',
                    'SAPSuccessFactorsGlobalConfiguration'
                ).current().provider_id,
                'launchURL': x['marketing_url'] or 'https://www.edx.org/',
                'contentTitle': 'Course Description',
                'contentID': x['key'],
                'launchType': 3,
                'mobileEnabled': x['mobile_available'],
            }
        ],
        'price': lambda x: [],
        'schedule': lambda x: [
            {
                'startDate': parse_datetime_to_epoch(x['start'] or UNIX_MIN_DATE_STRING),
                'endDate': parse_datetime_to_epoch(x['end'] or UNIX_MAX_DATE_STRING),
                'active': current_time_is_in_interval(x['start'], x['end']),
            }
        ],
        'revisionNumber': lambda x: 1,
    }


def parse_datetime_to_epoch(datestamp):
    """
    Convert an ISO-8601 datetime string to a Unix epoch timestamp in milliseconds.
    """
    parsed_datetime = parse_lms_api_datetime(datestamp)
    time_since_epoch = parsed_datetime - UNIX_EPOCH
    return int(time_since_epoch.total_seconds() * 1000)


def current_time_is_in_interval(start, end):
    """
    Determine whether the current time is on the interval [start, end].
    """
    interval_start = parse_lms_api_datetime(start or UNIX_MIN_DATE_STRING)
    interval_end = parse_lms_api_datetime(end or UNIX_MAX_DATE_STRING)
    return interval_start <= timezone.now() <= interval_end

"""Permanent public enclosure locator. A URL grants no access by itself."""
import re

REMOTE_ORIGIN = 'https://connect.atlantisllc.com'


def unit_url(serial):
    if not isinstance(serial, str) or not re.fullmatch(r'[A-Za-z0-9-]{1,24}', serial):
        raise ValueError('Invalid permanent enclosure serial')
    return REMOTE_ORIGIN + '/u/' + serial

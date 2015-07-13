# Licensed to Tomaz Muraus under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# Tomaz muraus licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging, pytz

from django.utils import timezone
from pygeoip import GeoIP, MEMORY_CACHE

from django_visitor_information import constants
from django_visitor_information import settings

__all__ = [
  'TimezoneMiddleware',
  'VisitorInformationMiddleware'
]

logger = logging.getLogger('django_visitor_information.middleware')
try:
  gi4 = GeoIP(settings.VISITOR_INFO_GEOIP_DATABASE_PATH, MEMORY_CACHE)
except IOError:
  print "no goip database :("
  gi4 = None
TIMEZONE_FIELD = getattr(settings,'USER_TIMEZONE_FIELD','timezone')

class TimezoneMiddleware(object):
  """
  This middleware activates a timezone for an authenticated user.

  This middleware assumes that a User model references a UserProfile model
  which has a "timezone" field.
  """
  def process_request(self, request):
    if request.path.startswith("/static") or request.path.startswith("/media"):
      return
    user = request.user
    user_timezone = None
    if TIMEZONE_FIELD:
      user_timezone = getattr(user, TIMEZONE_FIELD, None)

    if not user_timezone:
      timezone_name = request.session.get('django_timezone',None)
      if timezone_name:
        user_timezone = pytz.timezone(timezone_name)
      if not user_timezone and gi4:
        timezone_name = gi4.time_zone_by_addr(request.META['REMOTE_ADDR'])
        if timezone_name:
          user_timezone = pytz.timezone(timezone_name)
          request.session['django_timezone'] = timezone_name
      # Save us a little time next request
      if user_timezone and user.is_authenticated():
        setattr(user,TIMEZONE_FIELD,user_timezone)
        user.save()
      
    if not user_timezone:
      user_timezone = pytz.timezone(getattr(settings,'TIME_ZONE','America/Chicago'))

    try:
      timezone.activate(user_timezone)
    except Exception, e:
      extra = {'_user': request.user, '_timezone': user_timezone}
      logger.error('Invalid timezone selected: %s' % (str(e)), extra=extra)


class VisitorInformationMiddleware(object):
  """
  Middleware which adds the following keys to the request.visitor dictionary:
    - country
    - city
    - location.timezone
    - location.unit_system
    - user.timezone
    - user.unit_system
    - cookie_notice
  """
  def process_request(self, request):
    ip = request.META['REMOTE_ADDR']

    city = None
    country = None
    unit_system = None

    record = gi4.record_by_addr(ip)
    location_timezone = gi4.time_zone_by_addr(ip)

    if not location_timezone or not record:
      extra = {'_user': request.user, '_ip': ip}
      logger.debug('Couldn\'t detect timezone for ip', extra=extra)

    if record:
      city = record['city']
      country = record['country_name']

      if country in constants.COUNTRIES_WITH_IMPERIAL_SYSTEM:
        unit_system = 'imperial'
      else:
        unit_system = 'metric'

    cookie_notice = country in constants.COOKIE_NOTICE_PARTICIPATING_COUNTRIES

    request.visitor = {}
    request.visitor['country'] = country
    request.visitor['city'] = city
    request.visitor['location'] = {
      'timezone': location_timezone,
      'unit_system': unit_system
    }

    if request.user.is_authenticated():
      # If user is logged in, add current settings
      user = request.user
      user_timezone = getattr(user, settings.USER_TIMEZONE_FIELD, None)
      user_unit_system =  getattr(user, settings.USER_UNIT_SYSTEM_FIELD, None)
      request.visitor['user'] = {
        'timezone': user_timezone,
        'unit_system': user_unit_system
      }

    request.visitor['cookie_notice'] = cookie_notice

from django_visitor_information import settings
from django.core.management.base import BaseCommand, CommandError

import subprocess

class Command(BaseCommand):
    def handle (self, *args, **options):
        d = settings.VISITOR_INFO_GEOIP_DATABASE_PATH
        print d
        commands = [
            "curl http://geolite.maxmind.com/download/geoip/database/GeoLiteCity.dat.gz -o %s.gz"%d,
            "gunzip -f %s.gz"%d
        ]
        for command in commands:
            print command
            subprocess.Popen(command,stdout=subprocess.PIPE,shell=True).communicate()[0]

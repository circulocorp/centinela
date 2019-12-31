from classes.centinela import Centinela
from PydoNovosoft.utils import Utils
from threading import Thread
from time import sleep
import os
import json_logging
import logging
import sys


json_logging.ENABLE_JSON_LOGGING = True
json_logging.init()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))

config = Utils.read_config("package.json")
env_cfg = config[os.environ["environment"]]

if env_cfg["secrets"]:
    mzone_user = Utils.get_secret("centinelaz_user")
    mzone_pass = Utils.get_secret("centinelaz_pass")
    mzone_secret = Utils.get_secret("mzone_secret")
    centinela_token = Utils.get_secret("centinela_token")
    pghost = Utils.get_secret("pg_host")
    pguser = Utils.get_secret("pg_user")
    pgpass = Utils.get_secret("pg_pass")
else:
    mzone_user = env_cfg["mzone_user"]
    mzone_pass = env_cfg["mzone_pass"]
    mzone_secret = env_cfg["mzone_secret"]
    centinela_token = ""
    pghost = env_cfg["pg_host"]
    pguser = env_cfg["pg_user"]
    pgpass = env_cfg["pg_pass"]


def start(reporte):
    cent = Centinela(dbuser=pguser, dbpass=pgpass, dbhost=pghost, mzone_user=mzone_user,
                     mzone_pass=mzone_pass, mzone_secret=mzone_secret, token=centinela_token)
    cent.report_position(reporte)


def check_incomplete(cent):
    reportes = cent.get_incomplete_reports()
    for reporte in reportes:
        cent.update_unit(repote['Unit_Id'], reporte['id'])


def main():
    print(Utils.print_title("package.json"))
    cent = Centinela(dbuser=pguser, dbpass=pgpass, dbhost=pghost)
    while True:
        reportes = cent.get_open_reports()
        if len(reportes) < 1:
            check_incomplete(cent)
        for reporte in reportes:
            thread = Thread(target=start, args=(reporte,))
            thread.start()
        sleep(60)


if __name__ == '__main__':
    main()

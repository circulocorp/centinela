import requests
import base64 as b64
import psycopg2 as pg
import json
from PydoNovosoft.utils import Utils
from PydoNovosoft.scope.mzone import MZone
import json_logging
import logging
import sys


json_logging.ENABLE_JSON_LOGGING = True
json_logging.init()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))


class Centinela(object):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self._conn = None
        self.endpoint = "https://api-centinela.webmaps.com.mx/"

    def _connect(self):
        try:
            conn = pg.connect(host=self.dbhost, user=self.dbuser, password=self.dbpass, port="5432",
                              database="sos")
            self._conn = conn
        except (Exception, pg.Error) as error:
            logger.error(str(error), extra={'props': {"app": "centinela"}})
            print(error)

    def get_open_reports(self):
        sql = "select id,folio,marca,modelo,unidadyear,color,placa,vin,\"Unit_Id\", created,status,\"vehicle_Id\" from " \
              "centinela.reportes where status < 4 and \"vehicle_Id\" <>  '' "
        reports = []
        if not self._conn:
            self._connect()
        try:
            cursor = self._conn.cursor()
            cursor.execute(sql)
            data = cursor.fetchall()
            for row in data:
                report = {}
                report["id"] = row[0]
                report["folio"] = row[1]
                report["marca"] = row[2]
                report["modelo"] = row[3]
                report["unidadyear"] = row[4]
                report["color"] = row[5]
                report["placa"] = row[6]
                report["vin"] = row[7]
                report["Unit_Id"] = row[8]
                report["created"] = row[9]
                report["status"] = row[10]
                report["vehicle_Id"] = row[11]
                reports.append(report)
        except (Exception, pg.Error) as error:
            logger.error(str(error), extra={'props': {"app": "centinela"}})
        finally:
            logger.info("Active reports", extra={'props': {"app": "centinela", "data": reports}})
            return reports

    def get_incomplete_reports(self):
        sql = "select id,folio,marca,modelo,unidadyear,color,placa,vin,\"Unit_Id\", created,status,\"vehicle_Id\" from " \
              "centinela.reportes where status = 1 and \"vehicle_Id\" = '' "
        reports = []
        if not self._conn:
            self._connect()
        try:
            cursor = self._conn.cursor()
            cursor.execute(sql)
            data = cursor.fetchall()
            for row in data:
                report = {}
                report["id"] = row[0]
                report["folio"] = row[1]
                report["marca"] = row[2]
                report["modelo"] = row[3]
                report["unidadyear"] = row[4]
                report["color"] = row[5]
                report["placa"] = row[6]
                report["vin"] = row[7]
                report["Unit_Id"] = row[8]
                report["created"] = row[9]
                report["status"] = row[10]
                report["vehicle_Id"] = row[11]
                reports.append(report)
        except (Exception, pg.Error) as error:
            logger.error(str(error), extra={'props': {"app": "centinela"}})
        finally:
            logger.info("Getting Incomplete reports", extra={'props': {"app": "centinela"}})
            return reports

    def update_unit(self, vehicle, reporte):
        logger.info("Updating report", extra={'props': {"app": "centinela", "data": reporte}})
        mzone = MZone(self.mzone_user, self.mzone_pass, self.mzone_secret, "mz-a3tek")
        vehicles = mzone.get_vehicles(extra="unit_Description eq '"+str(vehicle)+"'")
        if len(vehicles) > 0:
            logger.info("Updating report", extra={'props': {"app": "centinela", "data": vehicles}})
            sql = "update centinela.reportes set \"vehicle_Id\"=%s where id=%s"
            if not self._conn:
                self._connect()
            cursor = self._conn.cursor()
            cursor.execute(sql, (vehicles[0]["id"], reporte))
            self._conn.commit()
        else:
            logger.info("No incomplete reports", extra={'props': {"app": "centinela"}})

    def _update_folio(self, report, rest):
        sql = "update centinela.reportes set folio=%s,status=%s where id=%s"
        if not self._conn:
            self._connect()
        cursor = self._conn.cursor()
        status = 2
        folio = None
        if not report["folio"] and rest["status"]:
            logger.info("The report doesn't have ID yet is consider as open",
                        extra={'props': {"app": "centinela", "data": rest["data"]}})
            folio = rest["data"]["folio"]
        else:
            folio = report["folio"]
            if rest["code"] == "REQUEST_LIMIT_EXCEEDED":
                logger.info("The reports limit was exceeded changing status to 5",
                            extra={'props': {"app": "centinela", "data": report}})
                status = 5
        cursor.execute(sql, (folio, status, report["id"]))
        self._conn.commit()

    def _generate_historic(self, report, position, rest):
        sql = "INSERT INTO centinela.reportehistorico(folio,latitud,longitud,velocidad,rumbo,log, created) " \
              "values(%s,%s,%s,%s,%s,%s, NOW())"
        if not self._conn:
            self._connect()
        cursor = self._conn.cursor()
        cursor.execute(sql, (report["folio"], position["latitude"], position["longitude"], position["speed"],
                             position["vehicle"]["odometer"], json.dumps(rest)))
        self._conn.commit()

    def report_position(self, report):
        mzone = MZone(self.mzone_user, self.mzone_pass, self.mzone_secret, "mz-a3tek")
        position = mzone.get_last_position(str(report["vehicle_Id"]))
        logger.info("Reporting position", extra={'props': {"app": "centinela", "data": report}})
        if position:
            token = b64.b64encode("centinela:"+self.token)
            headers = {"Authorization": "Bearer %s" % token, "Content-Type": "application/json"}
            resp = {}
            if not report["folio"]:
                data = {'fl': 0, 'ln': position["longitude"], 'lt': position["latitude"], 'vl': position["speed"],
                        'rm': position["vehicle"]["odometer"], 'pl': report["placa"], 'vn': report["vin"],
                        'mr': report["marca"], 'md': report["modelo"], 'an': report["unidadyear"], 'cl': report["color"],
                        'fc': Utils.format_date(Utils.datetime_zone(Utils.string_to_date(
                            position["utcTimestamp"], "%Y-%m-%dT%H:%M:%SZ"), "America/Mexico_City"), "%Y-%m-%d %H:%M:%S")}
                resp = requests.post(self.endpoint+"api/reporte", data=json.dumps(data), headers=headers, verify=False)
            else:
                data = {'fl': report["folio"], 'ln': position["longitude"], 'lt': position["latitude"],
                        'fc': Utils.format_date(Utils.datetime_zone(Utils.string_to_date(
                            position["utcTimestamp"], "%Y-%m-%dT%H:%M:%SZ"), "America/Mexico_City"), "%Y-%m-%d %H:%M:%S")}
                resp = requests.post(self.endpoint+"api/reporte", data=json.dumps(data), headers=headers, verify=False)
            logger.info("Sending position for report", extra={'props': {"app": "centinela",
                                                                        "data": report, "raw": resp.json()}})
            self._update_folio(report, resp.json())
            self._generate_historic(report, position, resp.json())

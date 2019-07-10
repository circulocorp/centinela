import requests
import base64 as b64
import psycopg2 as pg
import json
from PydoNovosoft.utils import Utils
from PydoNovosoft.scope.mzone import MZone


class Centinela(object):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self._conn = None
        self._endpoint = "https://api-centineladev.webmaps.com.mx/"

    def _connect(self):
        try:
            conn = pg.connect(host=self.dbhost, user=self.dbuser, password=self.dbpass, port="5432",
                              database="sos")
            self._conn = conn
        except (Exception, pg.Error) as error:
            print(error)

    def get_open_reports(self):
        sql = "select * from centinela.reportes where status < 4"
        reports = []
        if not self._conn:
            self._connect()
        try:
            cursor = self._conn.cursor()
            cursor.execute(sql)
            data = cursor.fetchall()
            for row in data:
                report = {}
                report["folio"] = row[1]
                report["marca"] = row[2]
                report["modelo"] = row[3]
                report["unidadyear"] = row[4]
                report["color"] = row[5]
                report["placa"] = row[6]
                report["vin"] = row[7]
                report["created"] = row[8]
                report["status"] = row[9]
                report["vehicle_id"] = row[10]
                reports.append(report)
        except (Exception, pg.Error) as error:
            print(error)
        finally:
            return reports

    def _update_folio(self, report, rest):
        sql = "update centinela.reportes set folio=%s,status=%s where id=%s"
        print(sql)
        if not self._conn:
            self._connect()
        try:
            cursor = self._conn.cursor()
            status = 2
            folio = None
            if rest["status"]:
                folio = rest["data"]["folio"]
            else:
                folio = report["folio"]
                if rest["code"] == "REQUEST_LIMIT_EXCEEDED":
                    status = 5
            cursor.execute(sql, (folio, status, report["id"]))
            self._conn.commit()
        except (Exception, pg.Error) as error:
            print(error)

    def _generate_historic(self, report, position, rest):
        sql = "INSERT INTO centinela.reportehistorico(folio,latitud,longitud,velocidad,rumbo,log, created) " \
              "values(%s,%s,%s,%s,%s,%s, NOW())"
        if not self._conn:
            self._connect()
        try:
            cursor = self._conn.cursor()
            cursor.execute(sql, (report["folio"], position["latitude"], position["longitude"], position["speed"],
                                 position["odometer"], rest.json()))
            self._conn.commit()
        except (Exception, pg.Error) as error:
            print(error)

    def report_position(self, report):
        mzone = MZone(self.mzone_user, self.mzone_pass, self.mzone_secret, "mz-a3tek")
        position = mzone.get_last_position(report["vehicle_id"])
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
                resp = requests.post(self._endpoint+"api/reporte", data=json.dumps(data), headers=headers, verify=False)
                self._update_folio(report, resp.json())
            else:
                data = {'fl': report["folio"], 'ln': position["longitude"], 'lt': position["latitude"],
                        'fc': Utils.format_date(Utils.datetime_zone(Utils.string_to_date(
                            position["utcTimestamp"], "%Y-%m-%dT%H:%M:%SZ"), "America/Mexico_City"), "%Y-%m-%d %H:%M:%S")}
                resp = requests.post(self._endpoint+"api/reporte", data=json.dumps(data), headers=headers, verify=False)
                self._update_folio(report, resp.json())
            self._generate_historic(report, position, resp.json())

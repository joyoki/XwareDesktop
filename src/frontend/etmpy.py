# -*- coding: utf-8 -*-

from PyQt5.QtCore import QObject, pyqtSignal
import threading, time
import requests
import collections

EtmSetting = collections.namedtuple("EtmSetting", ["dLimit", "uLimit", "maxRunningTasksNum"])

class EtmPy(QObject):
    sigTasksSummaryUpdated = pyqtSignal([bool], [dict])

    def __init__(self, app):
        super().__init__(app)
        self.app = app

        lcport = self.readRawETMConfigFile("etm.cfg", "local_control.listen_port")
        try:
            self.lcport = int(lcport)
        except (TypeError, ValueError):
            self.lcport = None

        self.peerid = self.readRawETMConfigFile("etm.cfg", "rc.peerid")
        self.t = threading.Thread(target = self.getCurrentTasksSummary, daemon = True)
        self.t.start()

    @property
    def lcontrol(self):
        return "http://127.0.0.1:{0}/".format(self.lcport)

    def getSettings(self):
        from requests.exceptions import ConnectionError
        try:
            req = requests.get(self.lcontrol + "getspeedlimit")
            limits = req.json()[1:] # not sure about what first element means, ignore for now

            req = requests.get(self.lcontrol + "getrunningtaskslimit")
            maxRunningTasksNum = req.json()[1]

            return EtmSetting(dLimit = limits[0], uLimit = limits[1],
                              maxRunningTasksNum = maxRunningTasksNum)
        except ConnectionError:
            return False

    def saveSettings(self, newsettings):
        requests.post(self.lcontrol + \
                      "settings?downloadSpeedLimit={}&uploadSpeedLimit={}&maxRunTaskNumber={}".format(*newsettings))

    def getCurrentTasksSummary(self):
        from requests.exceptions import ConnectionError
        while True:
            try:
                req = requests.get(self.lcontrol + "list?v=2&type=1&pos=0&number=0&needUrl=1")
                res = req.json()
                self.sigTasksSummaryUpdated[dict].emit(res)
            except ConnectionError:
                self.sigTasksSummaryUpdated[bool].emit(False)
            time.sleep(2)

    @staticmethod
    def readRawETMConfigFile(filename, key):
        with open("/opt/xware_desktop/xware/cfg/{}".format(filename), 'r') as file:
            lines = file.readlines()

        pairs = {}
        for line in lines:
            eq = line.index("=")
            k = line[:eq]
            v = line[(eq+1):]
            pairs[k] = v

        return pairs.get(key, None)

    def getActivationStatus(self):
        req = requests.get(self.lcontrol + "getsysinfo")
        code = req.json()[4] # activation code if not activated, empty string if activated

        if code:
            raise NotImplementedError
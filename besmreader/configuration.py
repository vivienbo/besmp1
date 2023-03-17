from croniter import croniter
from tzlocal import get_localzone
from pytz import timezone

import json
import os
from datetime import datetime

from .scheduler import P1Scheduler
from .processors import P1ProcessorFactory

class P1Configuration:

    """
        Configuration of the Belgian-SmartMeter-P1-to-MQTT
    """

    def __init__(self, configFileName: str):
        configFile = open(os.path.join(os.path.dirname(__file__), configFileName))
        self.configData = json.load(configFile)
        configFile.close()

        self.processors = dict()
        self.filters = None
        self.__init__scheduling()
        self.__init__processors()

    def __init__scheduling(self):
        for schedule in self.configData['scheduling']:
            localTimeZone=get_localzone()
            startDate = datetime.now(localTimeZone)

            schedule["cron"] = croniter(schedule["cron_format"], startDate)
            schedule["cron_next_trigger"] = schedule["cron"].get_next(datetime)

            if (schedule["mode"] == "average"):
                schedule["history"] = dict()
                for obisId in schedule["apply_to"]:
                    schedule["history"][obisId] = list()
        
        self.scheduler = P1Scheduler(self)
    
    def __init__processors(self):
        processorConfig = self.getProcessorsConfig()
        for processorName in processorConfig:
            self.processors[processorName] = P1ProcessorFactory.createProcessor(processorConfig[processorName])

    def closeProcessors(self):
        for processorName in self.processors:
             self.processors[processorName].closeProcessor()

    def getCOMPortConfig(self):
        if (not "timeout" in self.configData["COMPortConfig"]):
            self.configData["COMPortConfig"]["timeout"] = 5
        return self.configData["COMPortConfig"]
    
    def getTimeoutCycleLength(self) -> int:
        return self.getCOMPortConfig()["timeout"]

    def getP1Transformations(self):
        return self.configData["p1Transform"]
    
    def getScheduling(self):
        return self.configData["scheduling"]
    
    def getScheduler(self):
        return self.scheduler
    
    def getFilterSet(self):
        if (self.filters is None):
            uniqueFilters = set()
            for schedule in self.configData["scheduling"]:
                uniqueFilters.update(schedule["apply_to"])
            self.filters = uniqueFilters
        return self.filters

    def getProcessorsConfig(self):
        return self.configData["processors"]

    def getProcessor(self, processorName: str):
        return self.processors[processorName]
    
    def isHealthControlEnabled(self) -> bool:
        if ("healthControl" in self.configData):
            return self.configData["healthControl"]["enable"]
        return False

    # Default value is 2160 cycles
    def getHealthControlMaxLifetimeCycles(self) -> int:
        if (self.isHealthControlEnabled):
            return self.configData["healthControl"]["lifetime_cycles"]
        return 2160
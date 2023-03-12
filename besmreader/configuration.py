from cstriggers.core.trigger import QuartzCron
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
            startDate = datetime.now(timezone('UTC'))
            endDate = datetime.now(timezone('UTC')).replace(year = startDate.year + 10, day= 28)

            schedule["cron"] = QuartzCron(schedule_string=schedule["quartz"], start_date=startDate, end_date=endDate)
            
            # Resolves a bug from QuartzCron which does not set milliseconds at zero in the next_trigger
            schedule["cron_next_trigger"] = schedule["cron"].next_trigger().replace(microsecond=0)

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
        return self.configData["COMPortConfig"]
    
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

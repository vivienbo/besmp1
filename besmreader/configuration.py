from croniter import croniter
from tzlocal import get_localzone
from pytz import timezone

import logging
import logging.config
import json
import os
from datetime import datetime

from .scheduler import P1Scheduler
from .processors import P1ProcessorFactory, P1Processor

class P1ConfigurationError (Exception):
    """
        Exception in the P1Configuration of the overall module
    """

    def __init__(self, message="Configuration is incorrect"):
        super().__init__(self.message)


class P1Configuration:

    """
        Configuration of the Belgian-SmartMeter-P1-to-MQTT
    """

    def __init__(self, configFileName: str) -> None:
        try: 
            configFile = open(os.path.join(os.getcwd(), "config", configFileName))
            self._configData = json.load(configFile)
            configFile.close()
        except Exception as exceptionMet:
            raise P1ConfigurationError('Could not load configuration file: ' + str(exceptionMet))
        
        self._processors = dict()
        self._filters = None

        self.__init_configSchemaCheck()
        self.__init__scheduling()
        self.__init__processors()
        self.__init_serialPort()

    def __init__scheduling(self) -> None:
        for schedule in self._configData['scheduling']:
            localTimeZone=get_localzone()
            startDate = datetime.now(localTimeZone)

            schedule["cron"] = croniter(schedule["cronFormat"], startDate)
            schedule["cron_next_trigger"] = schedule["cron"].get_next(datetime)

            if (schedule["mode"] == "average"):
                schedule["history"] = dict()
                for obisId in schedule["applyTo"]:
                    schedule["history"][obisId] = list()
        
        self._scheduler = P1Scheduler(self)
    
    def __init__processors(self) -> None:
        processorConfig = self.__processorsConfig
        for processorName in processorConfig:
            self._processors[processorName] = P1ProcessorFactory.createProcessor(processorConfig[processorName])

    def __init_serialPort(self) -> None:
        # if no timeout is set, default value is 5 seconds
        if (not "timeout" in self._configData["SerialPortConfig"]):
            self._configData["SerialPortConfig"]["timeout"] = 5
        
        # since SmartMeter sends one packet per second, timeout should not be lower than 2 seconds
        if (self._configData["SerialPortConfig"]["timeout"] < 2):
            self._configData["SerialPortConfig"] = 2

    def __init_configSchemaCheck(self) -> None:
        # Set the Timezone information
        if ("core" in self._configData):
            if ("smartMeterTimeZone" in self._configData["core"]):
                self._configData["core"]["smartMeterTimeZone_pytz"] = timezone(self._configData["core"]["smartMeterTimeZone"])
        
        # default is to take the local system timezone
        self._configData["core"]["smartMeterTimeZone_pytz"] = get_localzone()

    def closeProcessors(self) -> None:
        for processorName in self._processors:
             self._processors[processorName].closeProcessor()

    @property
    def serialPortConfig(self) -> dict:
        return self._configData["SerialPortConfig"]
    
    @property
    def timeoutCycleLength(self) -> int:
        return self.serialPortConfig["timeout"]

    @property
    def p1Transformations(self) -> dict:
        return self._configData["p1Transform"]

    @property
    def scheduling(self) -> dict:
        return self._configData["scheduling"]
    
    @property
    def scheduler(self) -> P1Scheduler:
        return self._scheduler

    @property
    def filters(self) -> set:
        if (self._filters is None):
            uniqueFilters = set()
            for schedule in self._configData["scheduling"]:
                uniqueFilters.update(schedule["applyTo"])
            self._filters = uniqueFilters
        return self._filters

    @property
    def restartOnFailure(self) -> bool:
        if ("core" in self._configData):
            if ("restartOnFailure" in self._configData["core"]):
                return self._configData["core"]["restartOnFailure"]
        return False

    @property
    def smartMeterTimeZone(self) -> bool:
        return self._configData["core"]["smartMeterTimeZone_pytz"]

    @property
    def healthControlEnabled(self) -> bool:
        if ("healthControl" in self._configData):
            return self._configData["healthControl"]["enable"]
        return False
    
    @property
    def healthControlMaxLifetimeCycles(self) -> int:
        if (self.healthControlEnabled):
            return self._configData["healthControl"]["lifetimeCycles"]
        # default is 2160 cycles
        return 2160        

    @property
    def __processorsConfig(self) -> dict:
        return self._configData["processors"]

    def getProcessor(self, processorName: str) -> P1Processor:
        return self._processors[processorName]


class LoggerConfigurator:

    @staticmethod
    def loadConfiguration(logConfigFileName: str):
        configFile = open(logConfigFileName)
        logConfigData = json.load(configFile)
        configFile.close()
        logging.config.dictConfig(logConfigData)

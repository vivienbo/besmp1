from abc import abstractmethod
from paho.mqtt import client as paho

from .helper import LoggedClass
import logging
import ssl
import os

from .sequence import P1Sequence

class P1Processor:

    """
        Interface for all P1 Port information processors
    """

    def __init__(self, processorConfig: dict):
        self._processorConfig = processorConfig

    def processSequence(self, p1Sequence: P1Sequence, applyTo: dict):
        for label in applyTo:
            if (p1Sequence.hasInformation(label)):
                self.processInformation(self._processorConfig["topics"][label], p1Sequence.getInformationValue(label))
    
    @abstractmethod
    def processInformation(self, processLabel: str, processValue: str):
        pass

    @abstractmethod
    def closeProcessor(self):
        pass

    @staticmethod
    @abstractmethod
    def getConfigurationName() -> str:
        pass

class PrintP1Processor (P1Processor):

    """
        A P1 Port Information processor that prints data to stdout
    """

    def __init__(self, processorConfig: dict):
        super().__init__(processorConfig)

    def processInformation(self, processLabel: str, processValue: str):
        print(processLabel + " = " + str(processValue))

    def closeProcessor(self):
        pass
    
    @staticmethod
    def getConfigurationName() -> str:
        return "print"

class LoggerP1Processor (P1Processor, LoggedClass):

    def __init__(self, processorConfig: dict):
        if (not "logLevel" in processorConfig):
            processorConfig["logLevel"] = "INFO"
        self._loggerLevel = logging.__dict__[processorConfig["logLevel"]]
        P1Processor.__init__(self, processorConfig)
        LoggedClass.__init__(self)

    def processInformation(self, processLabel: str, processValue: str):
        super().logger.log(self._loggerLevel, '%s: %s', processLabel, str(processValue))

    def closeProcessor(self):
        pass

    @staticmethod
    def getConfigurationName() -> str:
        return "logger"


class MQTTP1Processor (P1Processor, LoggedClass):

    """
        A P1 Port Information processor that sends data to MQTT
    """

    @staticmethod
    def on_connect(client: paho.Client, userdata, flags, rc):
        if (rc==0):
            super().logger.info("MQTT: Connected successfully")
        else:
            super().logger.error("MQTT: Bad connection Returned code rc=", rc)

    def __init__(self, processorConfig: dict):
        P1Processor.__init__(self, processorConfig)
        LoggedClass.__init__(self)

        self._mqttClient = paho.Client(client_id="belgian-smartmeter-p1-to-mqtt")
        self._mqttClient.on_connect = MQTTP1Processor.on_connect
        
        if (('tls' in self._processorConfig) and (self._processorConfig['tls']['useTLS'])):
            rootCAFileName = 'config.crt'
            
            if ('rootCAFileName' in self._processorConfig['tls']):
                rootCAFileName = self._processorConfig['tls']['rootCAFileName']
            
            rootCAFilePath = os.path.abspath(os.path.join(os.getcwd(), 'config', rootCAFileName))
            self._mqttClient.tls_set(ca_certs=rootCAFilePath, tls_version=ssl.PROTOCOL_TLSv1_2, cert_reqs=ssl.CERT_NONE)
            
            if (('setTLSInsecure' in self._processorConfig['tls']) and (self._processorConfig['tls']['setTLSInsecure'])):
                self._mqttClient.tls_insecure_set(True)
        
        self._mqttClient.username_pw_set(self._processorConfig['username'], self._processorConfig['password'])
        self.connectMQTT()

    def connectMQTT(self):
        self._mqttClient.connect(self._processorConfig['broker'], self._processorConfig['tcpPort'], 60)    

    def processInformation(self, processLabel: str, processValue: str):
        if (not self._mqttClient.is_connected):
            self.connectMQTT()
        self._mqttClient.publish(topic=processLabel, payload=str(processValue))

    def closeProcessor(self):
        self._mqttClient.disconnect()
    
    @staticmethod
    def getConfigurationName() -> str:
        return "mqtt"

class P1ProcessorFactory:

    """
        A factory for creating P1 processors from a configuration.
    """
    _processorClassList = [MQTTP1Processor, PrintP1Processor, LoggerP1Processor]
    _procesorDictionary = None

    @classmethod
    def getProcessorDictionary(cls) -> dict:
        if (cls._procesorDictionary is None):
            cls._procesorDictionary = dict()
            for aClass in cls._processorClassList:
                cls._procesorDictionary[aClass.getConfigurationName()] = aClass

        return cls._procesorDictionary

    @classmethod
    def createProcessor(cls, processorConfig: dict):
        thisMap = cls.getProcessorDictionary()
        if (processorConfig["type"] in thisMap):
            return thisMap[processorConfig["type"]](processorConfig)
        
        raise P1ConfigurationError('Configuration error: Processor type does not exist: ' + processorConfig["type"]) # type: ignore
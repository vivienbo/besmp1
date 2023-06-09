from abc import abstractmethod
from paho.mqtt import client as paho
from jsonschema import validate as jsvalidate
from datetime import datetime, timedelta
import json

from .helper import LoggedClass
import logging
import ssl
import os

from .sequence import P1Sequence

class P1Processor:

    """
        Interface for all P1 Port information processors
    """

    def __init__(self, processorConfig: dict) -> None:
        self._processorConfig = processorConfig
        self.__init__validateSchema()

        if (len(self._processorConfig["topics"]) < 1):
            raise P1ConfigurationError('Configuration error: ' + self.__class__.__name__ + ' has no topics defined') # type: ignore

    def __init__validateSchema(self) -> None:
        schemaFileName = os.path.join(os.getcwd(), "schema", self.getConfigurationName() + '.processor.schema.json')
        jsonSchema = None
        
        if (os.path.exists(schemaFileName)):
            schemaFile = open(schemaFileName)
            jsonSchema = json.load(schemaFile)
            schemaFile.close()
            jsvalidate(self._processorConfig, jsonSchema)
        else:
            raise P1ConfigurationError('Configuration error: Could not find schema for processor: ' + self.getConfigurationName()) # type: ignore

    def processSequence(self, p1Sequence: P1Sequence, applyTo: dict) -> None:
        for obisCode in applyTo:
            if ((p1Sequence.hasInformation(obisCode)) and (obisCode in self._processorConfig["topics"])):
                self.processInformation(self._processorConfig["topics"][obisCode], p1Sequence.getInformationValue(obisCode), p1Sequence.getInformationUnit(obisCode))

    @abstractmethod
    def processInformation(self, processLabel: str, processValue: str, processUnit: str) -> None:
        pass

    @abstractmethod
    def closeProcessor(self) -> None:
        pass

    @staticmethod
    @abstractmethod
    def getConfigurationName() -> str:
        pass

class PrintP1Processor (P1Processor):

    """
        A P1 Port Information processor that prints data to stdout
    """

    def __init__(self, processorConfig: dict) -> None:
        super().__init__(processorConfig)

    def processInformation(self, processLabel: str, processValue: str, processUnit: str) -> None:
        print(processLabel + " = " + str(processValue) + " " + str(processUnit))

    def closeProcessor(self) -> None:
        pass
    
    @staticmethod
    def getConfigurationName() -> str:
        return "print"

class LoggerP1Processor (P1Processor, LoggedClass):

    def __init__(self, processorConfig: dict) -> None:
        P1Processor.__init__(self, processorConfig)
        LoggedClass.__init__(self)

        if (not "logLevel" in processorConfig):
            processorConfig["logLevel"] = "INFO"
        self._loggerLevel = logging.__dict__[processorConfig["logLevel"]]

    def processInformation(self, processLabel: str, processValue: str, processUnit: str) -> None:
        super().logger.log(self._loggerLevel, '%s: %s %s', processLabel, str(processValue), str(processUnit))

    def closeProcessor(self) -> None:
        pass

    @staticmethod
    def getConfigurationName() -> str:
        return "logger"


class MQTTP1Processor (P1Processor, LoggedClass):

    """
        A P1 Port Information processor that sends data to MQTT
    """

    def __init__(self, processorConfig: dict) -> None:
        P1Processor.__init__(self, processorConfig)
        LoggedClass.__init__(self)

        self.__already_connected_once = False
        self.__assume_connected = False
        self.__cooldown = None
        pahoClientInit = dict()

        pahoClientInit["transport"] = "tcp"
        if (("websockets" in self._processorConfig) and ("enabled" in self._processorConfig["websockets"]) and self._processorConfig["websockets"]["enabled"]):
            pahoClientInit["transport"] = "websockets"

        #
        # clientId name
        #
        pahoClientInit["client_id"] = "belgian-smartmeter-p1-to-mqtt"
        if ("clientId" in self._processorConfig):
            pahoClientInit["client_id"] = self._processorConfig["clientId"]
        
        #
        # Protocol detection and addition
        #
        if ("protocol" in self._processorConfig):
            pahoClientInit["protocol"] = paho.__dict__[self._processorConfig["protocol"]]

        self._mqttClient = paho.Client(**pahoClientInit)
        
        #
        # Websockets endpoint and headers configuration
        #
        if (pahoClientInit["transport"] == "websockets"):
            if (not "headers" in self._processorConfig["websockets"]):
                self._processorConfig["websockets"]["headers"] = None

            self._mqttClient.ws_set_options(self._processorConfig["websockets"]["path"], headers= self._processorConfig["websockets"]["headers"])

        if (('tls' in self._processorConfig) and (self._processorConfig['tls']['useTLS'])):
            tlsConfig = dict()
            rootCAFileName = 'config.crt'
            
            #
            # TLS connectivity parameters
            #
            if ('rootCAFileName' in self._processorConfig['tls']):
                rootCAFileName = self._processorConfig['tls']['rootCAFileName']
            
            tlsConfig["ca_certs"] = os.path.abspath(os.path.join(os.getcwd(), 'config', rootCAFileName))
            if ("tlsVersion" in self._processorConfig['tls']):
                tlsConfig["tls_version"] = ssl.__dict__[self._processorConfig['tls']['tlsVersion']]
            else:
                tlsConfig["tls_version"] = ssl.PROTOCOL_TLSv1_2
            
            if ("certReqs" in self._processorConfig['tls']):
                tlsConfig["cert_reqs"] = ssl.__dict__[self._processorConfig['tls']['certReqs']]
            else:
                tlsConfig["cert_reqs"] = ssl.CERT_NONE

            if("ciphers" in self._processorConfig['tls']):
                tlsConfig["ciphers"] = self._processorConfig['tls']['ciphers']

            #
            # TLS Authentication parameters
            #
            if (('certfile' in self._processorConfig['tls']) or ('keyfile' in self._processorConfig['tls'])):
                if ((('certfile' in self._processorConfig['tls']) and ('keyfile' in self._processorConfig['tls']))):
                    tlsConfig["certfile"] = os.path.abspath(os.path.join(os.getcwd(), 'config', self._processorConfig['tls']['certfile']))
                    tlsConfig["keyfile"] = os.path.abspath(os.path.join(os.getcwd(), 'config', self._processorConfig['tls']['keyfile']))
                else:
                    raise P1ConfigurationError("For TLS authentication, both 'certfile' and 'keyfile' must be provided") # type: ignore

            self._mqttClient.tls_set(**tlsConfig)
            
            if (('setTLSInsecure' in self._processorConfig['tls']) and (self._processorConfig['tls']['setTLSInsecure'])):
                self._mqttClient.tls_insecure_set(True)

            if (not 'port' in self._processorConfig):
                self._processorConfig['port'] = 8883
        
        #
        # Routine for username authentication
        #
        if ('username' in self._processorConfig):
            if (not 'password' in self._processorConfig):
                self._processorConfig['password'] = None
            
            self._mqttClient.username_pw_set(self._processorConfig['username'], self._processorConfig['password'])
        
        # catch potential mistake on password
        if ((not 'username' in self._processorConfig) and ('password' in self._processorConfig)):
            raise P1ConfigurationError('Missing username: MQTT Processor cannot have a password without a username') # type: ignore

        #
        # Port configuration
        #
        if (not 'port' in self._processorConfig):
            self._processorConfig['port'] = 1883

        self.connectMQTT()

    def connectMQTT(self) -> None:
        try:
            if ((self.__cooldown is None) or (datetime.now() >= self.__cooldown)):
                if (not self.__already_connected_once):
                    self._mqttClient.connect(self._processorConfig['broker'], self._processorConfig['port'], 60)
                    self.__already_connected_once = True
                    super().logger.info('MQTT connected for the first time')
                else:
                    self._mqttClient.reconnect()
                    super().logger.info('MQTT reconnected')
                self.__assume_connected = True
                self.__cooldown = None
        except:
            super().logger.error('MQTT (re)connect failed. Cooling down for 2 seconds.')
            self.__cooldown = datetime.now() + timedelta(seconds = 2)

    def processInformation(self, processLabel: str, processValue: str, processUnit: str) -> None:
        try:
            if (not self.__assume_connected):
                self.connectMQTT()
            self._mqttClient.publish(topic=processLabel, payload=str(processValue))
        except:
            super().logger.error('MQTT publish failed for %s %s', str(processValue), str(processUnit))
            super().logger.info('MQTT will try to reconnect on next schedule')
            self.__assume_connected = False

    def closeProcessor(self) -> None:
        try:
            self._mqttClient.disconnect()
        except:
            super().logger.error('MQTT disconnect failed')
    
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
    def createProcessor(cls, processorConfig: dict) -> None:
        thisMap = cls.getProcessorDictionary()
        if (processorConfig["type"] in thisMap):
            return thisMap[processorConfig["type"]](processorConfig)
        
        raise P1ConfigurationError('Configuration error: Processor type does not exist: ' + processorConfig["type"]) # type: ignore
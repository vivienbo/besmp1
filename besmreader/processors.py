from abc import abstractmethod
from paho.mqtt import client as paho

from .helper import LoggedClass
import ssl
import os

from .sequence import P1Sequence

class P1Processor:

    """
        Interface for all P1 Port information processors
    """

    def __init__(self, processorConfig: str):
        self.processorConfig = processorConfig

    def processSequence(self, p1Sequence: P1Sequence, applyTo: dict):
        for label in applyTo:
            if (p1Sequence.hasInformation(label)):
                self.processInformation(self.processorConfig["topics"][label], p1Sequence.getInformationValue(label))
    
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

class PrintP1Processor(P1Processor):

    """
        A P1 Port Information processor that prints data to stdout
    """

    def __init__(self, processorConfig: str):
        super().__init__(processorConfig)

    def processInformation(self, processLabel: str, processValue: str):
        print(processLabel + " = " + str(processValue))

    def closeProcessor(self):
        print("--- end processor ---")
    
    @staticmethod
    def getConfigurationName() -> str:
        return "print"

class MQTTP1Processor(P1Processor, LoggedClass):

    """
        A P1 Port Information processor that sends data to MQTT
    """

    @staticmethod
    def on_connect(client: paho.Client, userdata, flags, rc):
        if (rc==0):
            super().logger.info("MQTT: Connected successfully")
        else:
            super().logger.error("MQTT: Bad connection Returned code rc=", rc)

    def __init__(self, processorConfig: str):
        super().__init__(processorConfig)
        self.mqttClient = paho.Client(client_id="belgian-smartmeter-p1-to-mqtt")
        self.mqttClient.on_connect = MQTTP1Processor.on_connect
        
        crtFileName = os.path.abspath(os.path.join(os.getcwd(), 'config', 'config.crt'))
        self.mqttClient.tls_set(ca_certs=crtFileName, tls_version=ssl.PROTOCOL_TLSv1_2, cert_reqs=ssl.CERT_NONE)
        self.mqttClient.tls_insecure_set(True)
        
        self.mqttClient.username_pw_set(self.processorConfig['username'], self.processorConfig['password'])
        self.connectMQTT()

    def connectMQTT(self):
        self.mqttClient.connect(self.processorConfig['broker'], self.processorConfig['tcpPort'], 60)    

    def processInformation(self, processLabel: str, processValue: str):
        if (not self.mqttClient.is_connected):
            self.connectMQTT()
        self.mqttClient.publish(topic=processLabel, payload=str(processValue))

    def closeProcessor(self):
        self.mqttClient.disconnect()
    
    @staticmethod
    def getConfigurationName() -> str:
        return "mqtt"

class P1ProcessorFactory:

    """
        A factory for creating P1 processors from a configuration.
    """
    _processorClassList = [MQTTP1Processor, PrintP1Processor]
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
from paho.mqtt import client as paho

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
    
    def processInformation(self, processLabel: str, processValue: str):
        pass

    def closeProcessor(self):
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

class MQTTP1Processor(P1Processor):

    """
        A P1 Port Information processor that sends data to MQTT
    """

    def on_connect(client: paho.Client, userdata, flags, rc):
        if (rc==0):
            print("Connected successfully to MQTT")
        else:
            print("Bad connection Returned code rc=", rc)

    def __init__(self, processorConfig: str):
        super().__init__(processorConfig)
        self.mqttClient = paho.Client(client_id="belgian-smartmeter-p1-to-mqtt")
        self.mqttClient.on_connect=self.on_connect
        
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

class P1ProcessorFactory:

    """
        A factory for creating P1 processors from a configuration.
    """

    def createProcessor(processorConfig: dict):
        if (processorConfig["type"] == "print"):
            return PrintP1Processor(processorConfig)
        elif (processorConfig["type"] == "mqtt"):
            return MQTTP1Processor(processorConfig)
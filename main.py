import serial
import json
from cstriggers.core.trigger import QuartzCron
from pytz import timezone
from paho.mqtt import client as paho

import ssl
from queue import Queue, Empty
from threading import Thread, Semaphore, Event
from datetime import datetime
from decimal import Decimal
from statistics import mean
import re
import time

class P1Processor:

    def __init__(self, processorConfig):
        self.processorConfig = processorConfig

    def processSequence(self, p1Sequence, applyTo):
        for label in applyTo:
            if (p1Sequence.hasInformation(label)):
                self.processInformation(self.processorConfig["topics"][label], p1Sequence.getInformationValue(label))
    
    def processInformation(self, processLabel, processValue):
        pass

    def closeProcessor(self):
        pass

class PrintP1Processor(P1Processor):

    def __init__(self, processorConfig):
        super().__init__(processorConfig)

    def processInformation(self, processLabel, processValue):
        print(processLabel + " = " + str(processValue))

    def closeProcessor(self):
        print("--- end processor ---")

class MQTTP1Processor(P1Processor):

    def on_connect(client, userdata, flags, rc):
        if (rc==0):
            print("Connected successfully to MQTT")
        else:
            print("Bad connection Returned code rc=", rc)

    def __init__(self, processorConfig):
        self.mqttClient = paho.Client(client_id="py-readp1")
        self.mqttClient.on_connect=self.on_connect
        self.mqttClient.tls_set(r'.\readp1.crt', tls_version=ssl.PROTOCOL_TLSv1_2, cert_reqs=ssl.CERT_NONE)
        self.mqttClient.tls_insecure_set(True)
        self.mqttClient.username_pw_set(processorConfig['username'], processorConfig['password'])
        self.mqttClient.connect(processorConfig['broker'], processorConfig['tcpPort'], 60)
        super().__init__(processorConfig)

    def connectMQTT(self):
        self.mqttClient.connect(self.processorConfig['broker'], self.processorConfig['tcpPort'], 60)    

    def processInformation(self, processLabel, processValue):
        if (not self.mqttClient.is_connected):
            self.connectMQTT()
        self.mqttClient.publish(topic=processLabel, payload=str(processValue))

    def closeProcessor(self):
        self.mqttClient.disconnect()

class P1ProcessorFactory:

    def createProcessor(processorConfig):
        if (processorConfig["type"] == "print"):
            return PrintP1Processor(processorConfig)
        elif (processorConfig["type"] == "mqtt"):
            return MQTTP1Processor(processorConfig)

class P1Scheduler:

    def __init__(self, config):
        self.schedules = config.getScheduling()
        self.config = config

    def processP1(self, p1Sequence):
        p1Sequence.applyTransformations()

        for schedule in self.schedules:
            if (p1Sequence.getMessageTime() >= schedule["cron_next_trigger"]):
                self.processor = self.config.getProcessor(schedule["processor"])

                if (schedule["mode"] == "average"):
                    for obisId in schedule["apply_to"]:
                        if (len(schedule["history"][obisId])>0):
                            p1Sequence.addInformation(obisId, round(mean(schedule["history"][obisId]),3), p1Sequence.getInformationUnit(obisId))
                        schedule["history"][obisId].clear()

                self.processor.processSequence(p1Sequence, schedule["apply_to"])
                schedule["cron_next_trigger"] = schedule["cron"].next_trigger().replace(microsecond=0)
            else:
                if (schedule["mode"] == "average"):
                    for obisId in schedule["apply_to"]:
                        if (p1Sequence.hasInformation(obisId)):
                            schedule["history"][obisId].append(p1Sequence.getInformationValue(obisId))

class P1Configuration:

    def __init__(self, configFileName: str):
        configFile = open(configFileName)
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

    def getProcessor(self, processorName):
        return self.processors[processorName]

globalConfiguration = P1Configuration("readp1.json")

# A Thread that reads constantly from COM Port based on a given configuration. Can be stopped with stopReadingEvent shared accross threads
#
# @Author: Vivien Boistuaud
class ReadFromComPortThread (Thread):

    def __init__(self, rawDataQueue: Queue, stopReadingEvent: Event):
        Thread.__init__(self)
        self.rawDataQueue = rawDataQueue
        self.stopReadingEvent = stopReadingEvent
        self.daemon = True
        self.comPort = None
    
    def run(self):
        print('ReadFromComPortThread :: Starting...')
        try:
            serialConfig = globalConfiguration.getCOMPortConfig()
            self.comPort = serial.Serial(**serialConfig)
            while (not self.stopReadingEvent.is_set()):
                rawLine = self.comPort.readline()
                self.rawDataQueue.put(rawLine)
        except Exception as exceptionMet:
            print('ReadFromComPortThread :: Exception met :: ' + str(type(exceptionMet)))
            print(exceptionMet.args)
            print(exceptionMet)

        self.stopReadingEvent.set()
        self.closePort()
        print('ReadFromComPortThread :: Stopped')
    
    def closePort(self):
        if (self.comPort is not None):
            try: 
                self.comPort.close()
            except Exception:
                pass

class P1Sequence:
    
    def __init__(self, header):
        self.header = header
        self.signature = None
        self.informations = dict()
        self.utcMessageTime = None
        self.brusselsTimezone = timezone('Europe/Brussels')
        self.utcTimezone = timezone('UTC')

    def getMessageTime(self):
        return self.utcMessageTime
    
    def hasInformation(self, label):
        return label in self.informations

    def getInformationValue(self, label):
        if(label in self.informations):
            return self.informations[label]["value"]
        else:
            return 0

    def getInformationUnit(self, label):
        if(label in self.informations):
            if ("unit" in self.informations[label]):
                return self.informations[label]["unit"]
        else:
            return None

    def getSignature(self):
        return self.signature

    def setSignature(self, signature):
        self.signature = signature
    
    def addInformationFromDataLine(self, dataLine):
        if (self.keepAcceptingInformation()):
            reTimeStamp = re.findall(r'(0-0:1.0.0(\.\d+)?(\*\d+)?)\((\d+)([SW])\)', dataLine)
            reValueRead = re.findall(r'(\d+-\d+:\d+\.\d+\.\d+(\.\d+)?(\*\d+)?)\(((\d+(\.\d+)?)(\*(\w+))?)?\)', dataLine)

            if (reTimeStamp):
                self.setUTCMessageTime(reTimeStamp[0][3], reTimeStamp[0][4])
            elif (reValueRead):
                obisIdentifier = reValueRead[0][0]
                if (obisIdentifier in globalConfiguration.getFilterSet()):
                    obisValue = reValueRead[0][4]
                    obisUnit = reValueRead[0][7]
                    if (obisValue is not None):
                        if(re.findall(r'0-0:96\.1', obisIdentifier)):
                            self.informations[obisIdentifier] = {"value": obisValue, "unit": obisUnit}
                        else:
                            self.informations[obisIdentifier] = {"value": Decimal(obisValue), "unit": obisUnit}

    def addInformation(self, obisIdentifier, obisValue, obisUnit = 'kWh'):
        self.informations[obisIdentifier] = {"value": Decimal(obisValue), "unit": obisUnit}

    def setUTCMessageTime(self, dateTxt, tzTxt):
        is_dst = (tzTxt == "S")
        messageDate = datetime(year = int(dateTxt[0:2]) + 2000, month = int(dateTxt[2:4]), day = int(dateTxt[4:6]), hour = int(dateTxt[6:8]), minute = int(dateTxt[8:10]), second = int(dateTxt[10:12]))
        localMessageDateTime = self.brusselsTimezone.localize(messageDate, is_dst)
        self.utcMessageTime = localMessageDateTime.astimezone(self.utcTimezone)

    def keepAcceptingInformation(self):
        if (self.utcMessageTime == None):
            return True
        return True

    def applyTransformations(self):
        transformations = globalConfiguration.getP1Transformations()
        for id in transformations:
            result = 0
            if (transformations[id]["operation"] == "sum"):
                for operand in transformations[id]["operands"]:
                    result += self.getInformationValue(operand)
            self.addInformation(id, result)

    def __str__(self):
        theString = ""
        if self.signature is not None:
            theString = theString + f"P1Sequence {self.signature}:"
        if self.informations is not None:
            theString = theString + str(self.informations)
        return theString


class ParseP1RawDataThread (Thread):
    def __init__(self, rawDataQueue: Queue, p1SequenceQueue: Queue, stopReadingEvent: Event):
        Thread.__init__(self)
        self.rawDataQueue = rawDataQueue
        self.p1SequenceQueue = p1SequenceQueue
        self.stopReadingEvent = stopReadingEvent
        self.currentSequence = P1Sequence(None)
        self.daemon = True
    
    def run(self):
        print('ParseP1RawDataThread :: Starting...')
        try:
            while (not self.stopReadingEvent.is_set()):
                rawDataLine = self.rawDataQueue.get(True, 10)
                if (len(rawDataLine) > 2):
                    cleanDataLine = str(rawDataLine).rstrip()
                    if (self.isObjectStart(cleanDataLine)):
                        self.currentSequence = P1Sequence(cleanDataLine)
                    elif (self.isObjectEnd(cleanDataLine)):
                        self.currentSequence.setSignature(cleanDataLine)
                        self.p1SequenceQueue.put(self.currentSequence)
                    else:
                        self.currentSequence.addInformationFromDataLine(cleanDataLine)
        except Exception:
            print("ParseP1RawDataThread : Warning : no message received in 10 seconds")
        
        self.stopReadingEvent.set()
        print('ParseP1RawDataThread :: Stopped')

    def isObjectStart(self, data):
        return len(re.findall(r'/\w{4}\\', data)) != 0
    
    def isObjectEnd(self, data):
        return len(re.findall(r'![0-9A-F]{4}', data)) != 0

class ProcessP1SequencesThread (Thread):
    
    def __init__(self, p1SequenceQueue: Queue, stopReadingEvent: Event):
        Thread.__init__(self)
        self.p1SequenceQueue = p1SequenceQueue
        self.stopReadingEvent = stopReadingEvent
        self.averaging = dict()
        self.daemon = True
    
    def run(self):
        print('ProcessP1Sequences :: Starting...')

        try:
            while (not self.stopReadingEvent.is_set()):
                p1Sequence = self.p1SequenceQueue.get(True, 10)
                if (p1Sequence is not None):
                    globalConfiguration.getScheduler().processP1(p1Sequence)
        except Exception:
            print("ProcessP1SequencesThread : Warning : no message received in 10 seconds")

        self.stopReadingEvent.set()
        print('ProcessP1Sequences :: Stopped')

class HealthControllerThread (Thread):

    def __init__(self, stopReadingEvent: Event):
        Thread.__init__(self)
        self.stopReading = stopReadingEvent
        self.daemon = True
        self.counter = 2160
    
    def run(self):
        print("HealthControllerThread :: starting, will stop all threads in ~6 hours")
        while (not self.stopReading.is_set()) and (self.counter >= 0):
            self.counter -= 1
            time.sleep(10)

        if (self.counter <= 0):
            print("HealthControllerThread :: Trying to stop all threads")
            self.stopReading.set()
        
        print('HealthControllerThread :: Stopped')

while True:
    print('Creating Shared Event Controller')
    stopReadingEvent = Event()
    stopReadingEvent.clear()

    # Create the shared queues
    print('Creating Shared Queues')
    rawQueue = Queue()
    p1SequenceQueue = Queue()

    healthThread = HealthControllerThread(stopReadingEvent)
    processorThread = ProcessP1SequencesThread(p1SequenceQueue, stopReadingEvent)
    parserThread = ParseP1RawDataThread(rawQueue, p1SequenceQueue, stopReadingEvent)
    readerThread = ReadFromComPortThread(rawQueue, stopReadingEvent)

    processorThread.start()
    parserThread.start()
    readerThread.start()

    healthThread.start()

    while (not stopReadingEvent.is_set()):
        processorThread.join(0.1)
        if (not processorThread.is_alive()):
            stopReadingEvent.set()
        parserThread.join(0.1)
        if (not parserThread.is_alive()):
            stopReadingEvent.set()
        readerThread.join(0.1)
        if (not readerThread.is_alive()):
            stopReadingEvent.set()
        healthThread.join(0.1)

        if (not healthThread.is_alive()):
            stopReadingEvent.set()
        time.sleep(20)

    print('Waiting for threads to terminate...')
    readerThread.closePort()
    processorThread.join()
    parserThread.join()
    readerThread.join()
    # TODO:: Add health thread check

    print('All Threads terminated, relaunching...')

    print('Closing processors')
    globalConfiguration.closeProcessors()

    print('Reading P1 Configuration')
    configLoaded = False

    while (not configLoaded):
        try:
            globalConfiguration = P1Configuration("readp1.json")
            configLoaded = True
        except Exception as exceptionMet:
            print("Configuration could not be loaded: ", exceptionMet)
            time.sleep(5)

    time.sleep(5)
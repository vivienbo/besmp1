import serial

from queue import Queue
from threading import Thread, Event
import re
import time

from .sequence import P1Sequence

class ReadFromCOMPortThread(Thread):

    """
        A Thread which opens COM Port using PySerial and continuously read datalines until:
            * either an exception is met
            * or the stopReadingEvent is set
        
            Don't forget to set a timeout in the configuration or it can keep waiting for
            datalines forever without checking the stopReadingEvent
    """

    def __init__(self, rawDataQueue: Queue, stopReadingEvent: Event, configuration):
        Thread.__init__(self)
        self.rawDataQueue = rawDataQueue
        self.stopReadingEvent = stopReadingEvent
        self.daemon = True
        self.comPort = None
        self.globalConfiguration = configuration
    
    def run(self):
        print('ReadFromComPortThread :: Starting...')
        try:
            serialConfig = self.globalConfiguration.getCOMPortConfig()
            self.comPort = serial.Serial(**serialConfig)
            while (not self.stopReadingEvent.is_set()):
                rawLine = self.comPort.readline()
                self.rawDataQueue.put(rawLine)
        except Exception as exceptionMet:
            print('ReadFromComPortThread :: Exception met :: ' + str(type(exceptionMet)))
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

class ParseP1RawDataThread (Thread):

    """
        A Thread which interprets the rawDataLines from rawDataQueue to build P1 Sequence objects
        and transmit them to the p1SequenceQueue.
    """

    def __init__(self, rawDataQueue: Queue, p1SequenceQueue: Queue, stopReadingEvent: Event, configuration):
        Thread.__init__(self)
        self.rawDataQueue = rawDataQueue
        self.p1SequenceQueue = p1SequenceQueue
        self.stopReadingEvent = stopReadingEvent
        self.globalConfiguration = configuration

        self.currentSequence = P1Sequence(None, self.globalConfiguration)
        self.daemon = True
    
    def run(self):
        print('ParseP1RawDataThread :: Starting...')
        try:
            while (not self.stopReadingEvent.is_set()):
                rawDataLine = self.rawDataQueue.get(True, 10)
                if (len(rawDataLine) > 2):
                    cleanDataLine = str(rawDataLine).rstrip()
                    if (self.isObjectStart(cleanDataLine)):
                        self.currentSequence = P1Sequence(cleanDataLine, self.globalConfiguration)
                    elif (self.isObjectEnd(cleanDataLine)):
                        self.currentSequence.setSignature(cleanDataLine)
                        self.p1SequenceQueue.put(self.currentSequence)
                    else:
                        self.currentSequence.addInformationFromDataLine(cleanDataLine)
        except Exception as exceptionMet:
            print('ParseP1RawDataThread :: Exception met :: ' + str(type(exceptionMet)))
            print(exceptionMet)
            self.stopReadingEvent.set()
        
        print('ParseP1RawDataThread :: Stopped')

    def isObjectStart(self, data):
        return len(re.findall(r'/\w{4}\\', data)) != 0
    
    def isObjectEnd(self, data):
        return len(re.findall(r'![0-9A-F]{4}', data)) != 0

class ProcessP1SequencesThread(Thread):
    
    """
        A Thred which gets P1Sequence from the p1SequenceQueue and does calculations and processing
        as instructed by the P1Configuration
    """

    def __init__(self, p1SequenceQueue: Queue, stopReadingEvent: Event, configuration):
        Thread.__init__(self)
        self.p1SequenceQueue = p1SequenceQueue
        self.stopReadingEvent = stopReadingEvent
        self.averaging = dict()
        self.daemon = True
        self.globalConfiguration = configuration
    
    def run(self):
        print('ProcessP1Sequences :: Starting...')

        try:
            while (not self.stopReadingEvent.is_set()):
                p1Sequence = self.p1SequenceQueue.get(True, 10)
                if (p1Sequence is not None):
                    self.globalConfiguration.getScheduler().processP1(p1Sequence)
        except Exception as exceptionMet:
            print('ProcessP1SequencesThread :: Exception met :: ' + str(type(exceptionMet)))
            print(exceptionMet)
            self.stopReadingEvent.set()
        
        print('ProcessP1Sequences :: Stopped')

class HealthControllerThread (Thread):

    """
        A Thread which stops all other threads (by setting the stopReadingEvent) after a certain period of time.
        Used for troubleshooting and for monitoring period (unidentified issue with Quartz).
    """

    def __init__(self, stopReadingEvent: Event, configuration):
        Thread.__init__(self)
        self.stopReading = stopReadingEvent
        self.globalConfiguration = configuration

        self.daemon = True
        # Todo make counter configurable
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
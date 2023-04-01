import serial

from queue import Queue
from threading import Thread, Event
import re
import time

from .sequence import P1Sequence
from .helper import LoggedClass

class ReadFromCOMPortThread(Thread, LoggedClass):

    """
        A Thread which opens COM Port using PySerial and continuously read datalines until:
            * either an exception is met
            * or the stopReadingEvent is set
        
            Don't forget to set a timeout in the configuration or it can keep waiting for
            datalines forever without checking the stopReadingEvent
    """

    def __init__(self, rawDataQueue: Queue, stopReadingEvent: Event, configuration) -> None:
        LoggedClass.__init__(self)
        Thread.__init__(self)
        self.rawDataQueue = rawDataQueue
        self.stopReadingEvent = stopReadingEvent
        self.daemon = True
        self.comPort = None
        self.globalConfiguration = configuration
    
    def run(self) -> None:
        
        super().logger.info('Starting')
        try:
            self.comPort = serial.Serial(**self.globalConfiguration.serialPortConfig)
            while (not self.stopReadingEvent.is_set()):
                rawLine = self.comPort.readline()
                self.rawDataQueue.put(rawLine)
        except Exception as exceptionMet:
            super().logger.error('Exception while reading from serial: %s', str(type(exceptionMet)))
            super().logger.exception("Stack Trace")
            self.stopReadingEvent.set()

        self.closePort()
        super().logger.info('Stopped')
    
    def closePort(self) -> None:
        if (self.comPort is not None):
            try: 
                super().logger.info('Closing Serial Port')
                self.comPort.close()
            except Exception:
                pass

class ParseP1RawDataThread (Thread, LoggedClass):

    """
        A Thread which interprets the rawDataLines from rawDataQueue to build P1 Sequence objects
        and transmit them to the p1SequenceQueue.
    """

    def __init__(self, rawDataQueue: Queue, p1SequenceQueue: Queue, stopReadingEvent: Event, configuration) -> None:
        LoggedClass.__init__(self)
        Thread.__init__(self)
        self.rawDataQueue = rawDataQueue
        self.p1SequenceQueue = p1SequenceQueue
        self.stopReadingEvent = stopReadingEvent
        self.globalConfiguration = configuration

        self.currentSequence = P1Sequence(None, self.globalConfiguration)
        self.daemon = True
    
    def run(self) -> None:
        super().logger.info('Starting')
        try:
            while (not self.stopReadingEvent.is_set()):
                rawDataLine = self.rawDataQueue.get(True, self.globalConfiguration.timeoutCycleLength)
                if (len(rawDataLine) > 2):
                    cleanDataLine = str(rawDataLine).rstrip()
                    if (ParseP1RawDataThread.isObjectStart(cleanDataLine)):
                        self.currentSequence = P1Sequence(cleanDataLine, self.globalConfiguration)
                    elif (ParseP1RawDataThread.isObjectEnd(cleanDataLine)):
                        self.currentSequence.packetSignature = cleanDataLine
                        self.p1SequenceQueue.put(self.currentSequence)
                    else:
                        self.currentSequence.addInformationFromDataLine(cleanDataLine)
        except Exception as exceptionMet:
            if (not self.stopReadingEvent.is_set()):
                super().logger.error('Exception while parsing raw data: %s', str(type(exceptionMet)))
                super().logger.exception("Stack Trace")
                self.stopReadingEvent.set()
        
        super().logger.info('Stopped')

    @staticmethod
    def isObjectStart(data) -> bool:
        return len(re.findall(r'/\w{4}\\', data)) != 0
    
    @staticmethod
    def isObjectEnd(data) -> bool:
        return len(re.findall(r'![0-9A-F]{4}', data)) != 0

class ProcessP1SequencesThread(Thread, LoggedClass):
    
    """
        A Thred which gets P1Sequence from the p1SequenceQueue and does calculations and processing
        as instructed by the P1Configuration
    """

    def __init__(self, p1SequenceQueue: Queue, stopReadingEvent: Event, configuration) -> None:
        LoggedClass.__init__(self)
        Thread.__init__(self)
        self.p1SequenceQueue = p1SequenceQueue
        self.stopReadingEvent = stopReadingEvent
        self.averaging = dict()
        self.daemon = True
        self.globalConfiguration = configuration
    
    def run(self) -> None:
        super().logger.info('Starting...')

        try:
            while (not self.stopReadingEvent.is_set()):
                p1Sequence = self.p1SequenceQueue.get(True, self.globalConfiguration.timeoutCycleLength)
                if (p1Sequence is not None):
                    self.globalConfiguration.scheduler.processP1(p1Sequence)
        except Exception as exceptionMet:
            if (not self.stopReadingEvent.is_set()):
                super().logger.error('Exception processing sequences: %s', str(type(exceptionMet)))
                super().logger.exception("Stack Trace")
                self.stopReadingEvent.set()
        
        super().logger.info('Stopped')

class HealthControllerThread (Thread, LoggedClass):

    """
        A Thread which stops all other threads (by setting the stopReadingEvent) after a certain period of time.
        Used for troubleshooting and for monitoring period (unidentified issue with Quartz).
    """

    def __init__(self, stopReadingEvent: Event, configuration) -> None:
        LoggedClass.__init__(self)
        Thread.__init__(self)
        self.stopReading = stopReadingEvent
        self.globalConfiguration = configuration

        self.daemon = True
        # Todo make counter configurable
        self.counter = configuration.healthControlMaxLifetimeCycles

    
    def run(self) -> None:
        super().logger.info("Starting")
        super().logger.warning("Will restart all threads in %d seconds", self.counter * self.globalConfiguration.timeoutCycleLength)
        while (not self.stopReading.is_set()) and (self.counter >= 0):
            self.counter -= 1
            time.sleep(self.globalConfiguration.timeoutCycleLength)

        if (self.counter <= 0):
            super().logger.warning("Attempting to stop all threads now...")
            self.stopReading.set()
        
        super().logger.info('Stopped')

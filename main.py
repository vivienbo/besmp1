from collections import deque
from queue import Queue
from threading import Event
import logging
import time
import os
import signal

import besmreader.threads as besmThreads
from besmreader.helper import ThreadHelper

import besmreader.configuration as besmConfig

logger = logging.getLogger("besm")

"""
    Setup to stop the program properly using CTRL+C
"""
stopProgramEvent = Event()
sharedStopEvent = Event()

def beSMSignalHandler(sigNum, Frame):
    logger.info("Stopping the program when all threads are finished...")
    stopProgramEvent.set()
    sharedStopEvent.set()

signal.signal(signal.SIGINT, beSMSignalHandler)

"""
    Main program loop, launching and controlling threads execution
"""
while (not stopProgramEvent.is_set()):
    besmConfig.LoggerConfigurator.loadConfiguration(os.path.join(os.getcwd(), "config", "logger_config.json"))
    logger.info('Reading P1 Configuration')
    
    globalConfiguration = None
    configLoaded = False

    while (not configLoaded):
        try:
            globalConfiguration = besmConfig.P1Configuration(os.path.join(os.getcwd(), "config", "config.json"))
            configLoaded = True
        except Exception as exceptionMet:
            logger.error("Configuration could not be loaded: ", exceptionMet)
            time.sleep(5)

    # Create a shared event to stop all threads
    logger.info('Creating Shared Event Controller')
    sharedStopEvent = Event()

    # Create the shared queues
    logger.info('Creating Shared Queues')
    rawQueue = Queue()
    p1SequenceQueue = Queue()

    readerThread = besmThreads.ReadFromCOMPortThread(rawQueue, sharedStopEvent, globalConfiguration)

    threadsDeque = deque([
        besmThreads.ProcessP1SequencesThread(p1SequenceQueue, sharedStopEvent, globalConfiguration),
        besmThreads.ParseP1RawDataThread(rawQueue, p1SequenceQueue, sharedStopEvent, globalConfiguration),
        readerThread
    ])

    if (globalConfiguration.isHealthControlEnabled()):
        threadsDeque.appendleft(besmThreads.HealthControllerThread(sharedStopEvent, globalConfiguration))

    threadsList = list(threadsDeque)

    ThreadHelper.startAllThreads(*threadsList)

    while (not sharedStopEvent.is_set()):
        
        if(not ThreadHelper.checkAllThreadsAreAlive(*threadsList)):
            sharedStopEvent.set()
        
        time.sleep(20)

    logger.warning('Waiting for threads to terminate...')
    
    readerThread.closePort()
    ThreadHelper.waitForAllThreadsToFinish(*threadsList)
    logger.warning('All Threads terminated, relaunching...')

    logger.info('Closing processors')
    globalConfiguration.closeProcessors()

    time.sleep(globalConfiguration.getTimeoutCycleLength())
from queue import Queue
from threading import Event, Thread
import time
import os

import besmreader.threads as besmThreads
import besmreader.configuration as besmConfig

def checkAllThreadsAreAlive(*threads: Thread):
    allThreadsAreAlive = True
    for thisThread in threads:
        thisThread.join(0.1)
        allThreadsAreAlive = allThreadsAreAlive and thisThread.is_alive()
    return allThreadsAreAlive

def waitForAllThreadsToFinish(*threads: Thread):
    for thisThread in threads:
        thisThread.join()

def startAllThreads(*threads: Thread):
    for thisThread in threads:
        thisThread.start()

while True:
    print('Reading P1 Configuration')
    globalConfiguration = None
    configLoaded = False

    while (not configLoaded):
        try:
            globalConfiguration = besmConfig.P1Configuration(os.path.join(os.getcwd(), "config", "config.json"))
            configLoaded = True
        except Exception as exceptionMet:
            print("Configuration could not be loaded: ", exceptionMet)
            time.sleep(5)

    # Create a shared event to stop all threads
    print('Creating Shared Event Controller')
    stopReadingEvent = Event()

    # Create the shared queues
    print('Creating Shared Queues')
    rawQueue = Queue()
    p1SequenceQueue = Queue()

    healthThread = besmThreads.HealthControllerThread(stopReadingEvent, globalConfiguration)
    processorThread = besmThreads.ProcessP1SequencesThread(p1SequenceQueue, stopReadingEvent, globalConfiguration)
    parserThread = besmThreads.ParseP1RawDataThread(rawQueue, p1SequenceQueue, stopReadingEvent, globalConfiguration)
    readerThread = besmThreads.ReadFromCOMPortThread(rawQueue, stopReadingEvent, globalConfiguration)

    startAllThreads(processorThread, parserThread, readerThread, healthThread)

    while (not stopReadingEvent.is_set()):
        
        if(not checkAllThreadsAreAlive(processorThread, parserThread, readerThread, healthThread)):
            stopReadingEvent.set()
        
        time.sleep(20)

    print('Waiting for threads to terminate...')
    
    readerThread.closePort()
    waitForAllThreadsToFinish(processorThread, parserThread, readerThread, healthThread)
    print('All Threads terminated, relaunching...')

    print('Closing processors')
    globalConfiguration.closeProcessors()

    time.sleep(5)
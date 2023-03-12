from queue import Queue
from threading import Event
import time
import os

import besmreader.threads as besmThreads
import besmreader.configuration as besmConfig

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

    time.sleep(5)
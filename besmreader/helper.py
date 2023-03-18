import logging
from threading import Thread

class LoggedClass:

    def __init__(self) -> None:
        self._logger = logging.getLogger("besm." + self.__class__.__name__)

    @property
    def logger(self):
        return self._logger

class ThreadHelper:

    """
        A static class library that helps starting, stopping and checking the run status of a set of Thread's.
    """

    @staticmethod
    def startAllThreads(*threads: Thread) -> None:
        for thisThread in threads:
            thisThread.start()

    @staticmethod
    def checkAllThreadsAreAlive(*threads: Thread) -> bool:
        allThreadsAreAlive = True
        for thisThread in threads:
            thisThread.join(0.1)
            allThreadsAreAlive = allThreadsAreAlive and thisThread.is_alive()
        return allThreadsAreAlive

    @staticmethod
    def waitForAllThreadsToFinish(*threads: Thread) -> None:
        for thisThread in threads:
            thisThread.join()
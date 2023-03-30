from statistics import mean
from datetime import datetime
from collections import deque

from .sequence import P1Sequence


class P1Scheduler:

    def __init__(self, config):
        self.__schedules = config.scheduling
        self.__config = config
        self.__cachedSequences = dict()

    def processP1(self, p1Sequence: P1Sequence) -> None:
        if (not p1Sequence.hasTimeinSystemTimezone):
            return
        
        p1Sequence.applyTransformations()

        scheduleIndex = 0
        while (scheduleIndex < len(self.__schedules)):
            schedule = self.__schedules[scheduleIndex]
            applyToSchedule = schedule["applyTo"]

            if (p1Sequence.messageTimeinSystemTimezone >= schedule["cron_next_trigger"]):
                self.processor = self.__config.getProcessor(schedule["processor"])

                if (schedule["mode"] == "average"):
                    for obisId in applyToSchedule:
                        if (len(schedule["history"][obisId])>0):
                            p1Sequence.addInformation(obisId, round(mean(schedule["history"][obisId]),3), p1Sequence.getInformationUnit(obisId))
                        schedule["history"][obisId].clear()

                if (schedule["mode"] == "changed"):
                    formerSequence = self.__cachedSequences.get(scheduleIndex)
                    if (not formerSequence is None):
                        actualApplyTo = deque()
                        for obisCode in applyToSchedule:
                            if (p1Sequence.getInformationValue(obisCode) != self.__cachedSequences[scheduleIndex].getInformationValue(obisCode)):
                                actualApplyTo.append(obisCode)
                        applyToSchedule = list(actualApplyTo)
                    
                    self.__cachedSequences[scheduleIndex] = p1Sequence
                    pass

                self.processor.processSequence(p1Sequence, applyToSchedule)
                #self.__cachedSequences[schedule]
                schedule["cron_next_trigger"] = schedule["cron"].get_next(datetime)
            else:
                if (schedule["mode"] == "average"):
                    for obisId in applyToSchedule:
                        if (p1Sequence.hasInformation(obisId)):
                            schedule["history"][obisId].append(p1Sequence.getInformationValue(obisId))
            scheduleIndex += 1
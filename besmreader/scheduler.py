from statistics import mean
from datetime import datetime
from collections import deque

from .sequence import P1Sequence


class P1Scheduler:

    def __init__(self, config):
        self.__schedules = config.scheduling
        self.__config = config

    def processP1(self, p1Sequence: P1Sequence) -> None:
        if (not p1Sequence.hasTimeinSystemTimezone):
            return
        
        p1Sequence.applyTransformations()

        for schedule in self.__schedules:
            if ((p1Sequence.hasTimeinSystemTimezone) and (p1Sequence.messageTimeinSystemTimezone >= schedule["cron_next_trigger"])):
                self.processor = self.__config.getProcessor(schedule["processor"])

                self._doAddAveragesOnChronTrigger(schedule, p1Sequence)
                applyToSchedule = self._doFilterApplyToScheduleOnChronTrigger(schedule, p1Sequence)

                self.processor.processSequence(p1Sequence, applyToSchedule)
                schedule["cron_next_trigger"] = schedule["cron"].get_next(datetime)
            else:
                self._doAverageChronNotTime(schedule, p1Sequence)

    def _doAddAveragesOnChronTrigger(self, schedule: dict, p1Sequence: P1Sequence) -> None:
        if (schedule["mode"] == "average"):
            for obisId in schedule["applyTo"]:
                if (len(schedule["history"][obisId])>0):
                    p1Sequence.addInformation(obisId, round(mean(schedule["history"][obisId]),3), p1Sequence.getInformationUnit(obisId))
                schedule["history"][obisId].clear()

    def _doFilterApplyToScheduleOnChronTrigger(self, schedule: dict, p1Sequence: P1Sequence) -> list:
        applyToSchedule = schedule["applyTo"]

        if (schedule["mode"] == "changed"):
            formerSequence = schedule.get("_previousSequence")
            if (not formerSequence is None):
                actualApplyTo = deque()
                for obisCode in applyToSchedule:
                    if (p1Sequence.getInformationValue(obisCode) != schedule["_previousSequence"].getInformationValue(obisCode)):
                        actualApplyTo.append(obisCode)
                applyToSchedule = list(actualApplyTo)
            
            schedule["_previousSequence"] = p1Sequence
        
        return applyToSchedule

    def _doAverageChronNotTime(self, schedule: dict, p1Sequence: P1Sequence) -> None:
        if (schedule["mode"] == "average"):
            for obisId in schedule["applyTo"]:
                if (p1Sequence.hasInformation(obisId)):
                    schedule["history"][obisId].append(p1Sequence.getInformationValue(obisId))
from statistics import mean
from .sequence import P1Sequence

class P1Scheduler:

    def __init__(self, config):
        self.schedules = config.getScheduling()
        self.config = config

    def processP1(self, p1Sequence: P1Sequence):
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
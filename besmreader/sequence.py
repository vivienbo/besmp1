from pytz import timezone
from datetime import datetime
from decimal import Decimal
import re

class P1Sequence:
    
    """
        A P1Sequence is a set of OBIS-format information starting with a \FLU sequence
        and ending with a !ABCD hash.
    """

    def __init__(self, header: str, configuration):
        self.header = header
        self.signature = None
        self.informations = dict()
        self.utcMessageTime = None
        self.brusselsTimezone = timezone('Europe/Brussels')
        self.utcTimezone = timezone('UTC')
        self.globalConfiguration = configuration

    def getMessageTime(self):
        return self.utcMessageTime
    
    def hasInformation(self, label: str):
        return label in self.informations

    def getInformationValue(self, label: str):
        if(label in self.informations):
            return self.informations[label]["value"]
        else:
            return 0

    def getInformationUnit(self, label: str):
        if(label in self.informations):
            if ("unit" in self.informations[label]):
                return self.informations[label]["unit"]
        else:
            return None

    def getSignature(self):
        return self.signature

    def setSignature(self, signature: str):
        self.signature = signature
    
    def addInformationFromDataLine(self, dataLine: str):
        if (self.keepAcceptingInformation()):
            reTimeStamp = re.findall(r'(0-0:1.0.0(\.\d+)?(\*\d+)?)\((\d+)([SW])\)', dataLine)
            reValueRead = re.findall(r'(\d+-\d+:\d+\.\d+\.\d+(\.\d+)?(\*\d+)?)\(((\d+(\.\d+)?)(\*(\w+))?)?\)', dataLine)

            if (reTimeStamp):
                self.setUTCMessageTime(reTimeStamp[0][3], reTimeStamp[0][4])
            elif (reValueRead):
                obisIdentifier = reValueRead[0][0]
                if (obisIdentifier in self.globalConfiguration.getFilterSet()):
                    obisValue = reValueRead[0][4]
                    obisUnit = reValueRead[0][7]
                    if (obisValue is not None):
                        if(re.findall(r'0-0:96\.1', obisIdentifier)):
                            self.informations[obisIdentifier] = {"value": obisValue, "unit": obisUnit}
                        else:
                            self.informations[obisIdentifier] = {"value": Decimal(obisValue), "unit": obisUnit}

    def addInformation(self, obisIdentifier: str, obisValue: float, obisUnit: str = 'kWh'):
        self.informations[obisIdentifier] = {"value": Decimal(obisValue), "unit": obisUnit}

    def setUTCMessageTime(self, dateTxt: str, tzTxt: str):
        is_dst = (tzTxt == "S")
        messageDate = datetime(year = int(dateTxt[0:2]) + 2000, month = int(dateTxt[2:4]), day = int(dateTxt[4:6]), hour = int(dateTxt[6:8]), minute = int(dateTxt[8:10]), second = int(dateTxt[10:12]))
        localMessageDateTime = self.brusselsTimezone.localize(messageDate, is_dst)
        self.utcMessageTime = localMessageDateTime.astimezone(self.utcTimezone)

    def keepAcceptingInformation(self):
        if (self.utcMessageTime == None):
            return True
        return True

    def applyTransformations(self):
        transformations = self.globalConfiguration.getP1Transformations()
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
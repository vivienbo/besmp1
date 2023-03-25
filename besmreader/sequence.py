from pytz import timezone
from tzlocal import get_localzone

from datetime import datetime
from decimal import Decimal
import re

class P1Sequence:
    
    """
        A P1Sequence is a set of OBIS-format information starting with a \FLU sequence
        and ending with a !ABCD hash.
    """

    def __init__(self, header: str, configuration):
        self._packetHeader = header
        self._packetSignature = None
        self._informations = dict()
        self._systemTimeZoneMessageTime = None
        self._smartMeterTimezone = configuration.smartMeterTimeZone
        self._systemTimeZone = get_localzone()
        self._config = configuration

    @property
    def messageTimeinSystemTimezone(self) -> datetime:
        return self._systemTimeZoneMessageTime
    
    @property
    def hasTimeinSystemTimezone(self) -> bool:
        return (self.__setMessageTimeInSystemTimezone is not None)

    @property
    def packetSignature(self) -> str:
        return self._packetSignature

    @property
    def hasPacketSignature(self) -> bool:
        return (not self.packetSignature is None)

    @packetSignature.setter
    def packetSignature(self, signature: str):
        self._packetSignature = signature

    #
    # This routine tries to split the OBIS Code into two parts:
    # * The standard OBIS code in format 0-0:0.0.0.0*0
    # * The specific format added to get multivalues: "/0"
    #
    # returns a list of (OBISCode, multiValueIndex)
    #
    def _splitInformationOBISCode(self, obisCode: str) -> tuple[str, int]:
        foundLabels = obisCode.split('/')
        if (foundLabels):
            if (len(foundLabels) < 2):
                foundLabels.append("0")
            return foundLabels[0], int(foundLabels[1])
        else:
            return None, None

    def hasInformation(self, obisCode: str):
        label, subItem = self._splitInformationOBISCode(obisCode)
        return (label in self._informations) and (len(self._informations[label]) > subItem)

    def getInformationValue(self, obisCode: str):
        label, subItem = self._splitInformationOBISCode(obisCode)
        if(label in self._informations):
            if (len(self._informations[label]) > subItem):
                return self._informations[label][subItem]["value"]

        return 0

    def getInformationUnit(self, obisCode: str):
        label, subItem = self._splitInformationOBISCode(obisCode)
        if(label in self._informations):
            if (len(self._informations[label]) > subItem):
                if ("unit" in self._informations[label][subItem]):
                    return self._informations[label][subItem]["unit"]

        return None
    
    def addInformationFromDataLine(self, dataLine: str):
        if (self.__keepAcceptingInformation()):
            reTimeStamp = re.findall(r'(0-0:1.0.0(\.\d+)?(\*\d+)?)\((\d+)([SW])\)', dataLine)
            reValueRead = re.findall(r'(\d+-\d+:\d+\.\d+\.\d+(\.\d+)?(\*\d+)?)\(((\d+(\.\d+)?)(\*(\w+))?)?\)', dataLine)

            if (reTimeStamp):
                self.__setMessageTimeInSystemTimezone(reTimeStamp[0][3], reTimeStamp[0][4])
            elif (reValueRead):
                obisIdentifier = reValueRead[0][0]
                if (obisIdentifier in self._config.filters):
                    obisValue = reValueRead[0][4]
                    obisUnit = reValueRead[0][7]
                    if (obisValue is not None):
                        if(re.findall(r'0-0:96\.1', obisIdentifier)):
                            self._informations[obisIdentifier] = [
                                {
                                    "value" : obisValue,
                                    "unit": obisUnit
                                }
                            ]
                        else:
                            self._informations[obisIdentifier] = [
                                {
                                    "value": Decimal(obisValue),
                                    "unit": obisUnit
                                }
                            ]

    def addInformation(self, obisIdentifier: str, obisValue: float, obisUnit: str = 'kWh'):
        self._informations[obisIdentifier] = [
            {
                "value": Decimal(obisValue),
                "unit": obisUnit
            }
        ]

    def __setMessageTimeInSystemTimezone(self, dateTxt: str, tzTxt: str):
        is_dst = (tzTxt == "S")
        messageDate = datetime(year = int(dateTxt[0:2]) + 2000, month = int(dateTxt[2:4]), day = int(dateTxt[4:6]), hour = int(dateTxt[6:8]), minute = int(dateTxt[8:10]), second = int(dateTxt[10:12]))
        localMessageDateTime = self._smartMeterTimezone.localize(messageDate, is_dst)
        self._systemTimeZoneMessageTime = localMessageDateTime.astimezone(self._systemTimeZone)

    def __keepAcceptingInformation(self):
        return (not self.hasPacketSignature)

    def applyTransformations(self):
        transformations = self._config.p1Transformations
        for id in transformations:
            info = dict()
            result = 0
            if (transformations[id]["operation"] == "sum"):
                for operand in transformations[id]["operands"]:
                    result += self.getInformationValue(operand)
            
            info["obisIdentifier"] = id
            info["obisValue"] = result
            if ("unit" in transformations[id]):
                info["obisUnit"] = transformations[id]["unit"]

            self.addInformation(**info)

    def __str__(self):
        theString = ""
        if self._packetSignature is not None:
            theString = theString + f"P1Sequence {self._packetSignature}:"
        if self._informations is not None:
            theString = theString + str(self._informations)
        return theString
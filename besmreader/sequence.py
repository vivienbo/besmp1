from pytz import timezone
from tzlocal import get_localzone

from collections import deque
from datetime import datetime
from decimal import Decimal
import re

class P1Sequence:
    
    """
        A P1Sequence is a set of OBIS-format information starting with a \FLU sequence
        and ending with a !ABCD hash.
    """
    OBIS_PACKET_DATE = r'0-0:1.0.0'
    REGEXP_OBIS_CODE_AND_VALUES = r'((\d+-\d+:\d+\.\d+\.\d+(\.\d+)?(\*\d+)?)(\([\w ,.!?/*-+=:]*\))+)'
    REGEXP_OBIS_VALUE_DATE = r'(\d+)([SW])'
    REGEXP_OBIS_VALUE_DECIMAL = r'((\d+(\.\d+)?)(\*(\w+))*)$'
    REGEXP_OBIS_VALUE_TEXT = r'([\w ,.!?/*-+=:]*)'
    REGEXP_OBIS_VALUE_CODE = r'(\d+-\d+:\d+\.\d+\.\d+(\.\d+)?(\*\d+)?)'

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
    
    def getInformationType(self, obisCode: str):
        label, subItem = self._splitInformationOBISCode(obisCode)
        if(label in self._informations):
            if (len(self._informations[label]) > subItem):
                if ("unit" in self._informations[label][subItem]):
                    return type(self._informations[label][subItem]["value"])
        
        return None

    def addInformationFromDataLine(self, dataLine: str):
        if (self.__keepAcceptingInformation()):
            foundOBISInfo = re.findall(P1Sequence.REGEXP_OBIS_CODE_AND_VALUES, dataLine)

            if (foundOBISInfo):
                # Remove parenthesis before and after values
                obisData = foundOBISInfo[0][0].split("(")
                i = 0
                while i < len(obisData):
                    obisData[i] = obisData[i].replace(")", "")
                    i += 1
                
                obisIdentifier = obisData[0]
                # OBIS Code is 0, the rest are values
                if (obisIdentifier == P1Sequence.OBIS_PACKET_DATE):
                    obisIsDate = re.findall(P1Sequence.REGEXP_OBIS_VALUE_DATE, obisData[1])
                    if (obisIsDate):
                        self.__setMessageTimeInSystemTimezone(obisIsDate[0][0], obisIsDate[0][1])
                else:
                    try:
                        obisContents = deque()
                        for obisValue in obisData[1:]:
                            obisIsValueDecimal = re.findall(P1Sequence.REGEXP_OBIS_VALUE_DECIMAL, obisValue)
                            if (obisIsValueDecimal):
                                theValue = Decimal(obisIsValueDecimal[0][1])
                                theUnit = obisIsValueDecimal[0][4]
                                theData = {
                                    "value": theValue
                                }
                                if (theUnit != ''):
                                    theData["unit"] = theUnit
                                obisContents.append(theData)
                                pass
                            else:
                                obisIsValueDate = re.findall(P1Sequence.REGEXP_OBIS_VALUE_DATE, obisValue)
                                if (obisIsValueDate):
                                    dateTxt = obisIsValueDate[0][0]
                                    tzTxt = obisIsValueDate[0][1]

                                    is_dst = (tzTxt == "S")
                                    thisDate = datetime(year = int(dateTxt[0:2]) + 2000, month = int(dateTxt[2:4]), day = int(dateTxt[4:6]), hour = int(dateTxt[6:8]), minute = int(dateTxt[8:10]), second = int(dateTxt[10:12]))
                                    localThisDateTime = self._smartMeterTimezone.localize(thisDate, is_dst)
                                    obisContents.append({
                                        "value": localThisDateTime.astimezone(self._systemTimeZone)
                                    })
                                else:
                                    obisIsValueCode = re.findall(P1Sequence.REGEXP_OBIS_VALUE_CODE, obisValue)
                                    if (obisIsValueCode):
                                        theCode = obisIsValueCode[0][0]
                                        obisContents.append({
                                            "value": theCode
                                        })
                                    else:
                                        obisIsValueText = re.findall(P1Sequence.REGEXP_OBIS_VALUE_TEXT, obisValue)
                                        if (obisIsValueText):
                                            theText = obisIsValueText[0]
                                            obisContents.append({
                                                "value": theText
                                            })

                        self._informations[obisIdentifier] = list(obisContents)
                    except Exception as exceptionMet:
                        super().logger.debug('Exception while parsing OBIS data: %s', str(type(exceptionMet)))
                        super().logger.info('OBIS dataline not parsed: %s', str(dataLine))
                        pass

    def addInformation(self, obisIdentifier: str, obisValue: float, obisUnit: str = None):
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
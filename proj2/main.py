import xml.etree.ElementTree as ET
import sys
import re


# definice konstant
errLexSynt = 23

errWrongXMLFormat = 31
errUnexpectedStruct = 32

errSemantic = 52
errWrongOperandType = 53
errGettingNotExistVar = 54
errFrameNotExist = 55
errMissingValue = 56
errWrongOperandValue = 57
errWrongStringOperation = 58

class Frame:
    def __init__(self):
        self.dict = {}
        self.isInitialized = False

    def checkInitialized(self):
        if not self.isInitialized:
            errorExit("Ramec neexistuje", errFrameNotExist)

lineNr = 1

class Runtime:
    def __init__(self, srcName):
        self.GF = Frame()
        self.LF = Frame()
        self.TF = Frame()
        self.GF.isInitialized = True
        self.act_frame = self.GF
        self.program = []
        self.labels = {}
        try:
            self.parser = XMLParser(srcName) # spec_example.out
        except ET.ParseError as e:
            errorExit("Chyba pri parsovani XML", errWrongXMLFormat)

    def getLinesLabels(self):
        global lineNr
        for instr in self.parser.root:
            print(instr.attrib)
            if int(instr.get("order", default=0)) != lineNr:
                errorExit("Spatne cislo radku!", errUnexpectedStruct)
            else:
                lineNr += 1

            opCode = instr.get("opcode", default="UNKNOWN")
            arg1 = instr.find("arg1")
            if arg1 == None:
                errorExit("Nemame arg1!", errUnexpectedStruct)
            arg1Text = arg1.text
            order = instr.get("order", default=0)
            self.program.append([order])
            if opCode == "LABEL":
                self.labels[arg1Text] = order

    # def isVarName(self, varName):
    #     return varName[:3] == "GF@" or varName[:3] == "LF@" or varName[:3] == "TF@"

    def checkFrameVar(self, varName):
        if varName[:3] == "GF@":
            self.act_frame = self.GF
        elif varName[:3] == "LF@":
            self.act_frame = self.LF
        elif varName[:3] == "TF@":
            self.act_frame = self.TF
        else:
            errorExit("Pokus o manipulaci s neexistujicim ramcem", errFrameNotExist)

        self.actVarName = varName[3:]
        self.act_frame.checkInitialized()

    def isVarDefined(self, varName):
        self.checkFrameVar(varName)
        return self.actVarName in self.act_frame.dict

    def defineVar(self, varName):
        self.checkFrameVar(varName)
        if self.isVarDefined(varName):
            errorExit("Promenna je jiz definovana!", errSemantic)
        else:
            self.act_frame.dict[self.actVarName] = None

    def getVar(self, varName):
        self.checkFrameVar(varName)
        if not self.isVarDefined(varName):
            errorExit("Promenna neni definovana!", errSemantic)
        else:
            return self.act_frame.dict[self.actVarName]

    def setVar(self, varName, type, value):
        self.checkFrameVar(varName)
        if not self.isVarDefined(varName):
            errorExit("Promenna neni definovana!", errSemantic)
        else:
            if type == "string" and value == None:
                value = ""
            self.act_frame.dict[self.actVarName] = value

    def strHexToChar(self, inputString):
        return re.sub(r'\\(\d{3})', lambda match: chr(int(match.group(1))), inputString)

    def mustHaveArg2(self, arg2):
        if arg2 == None:
            errorExit("Nemame arg2!", errUnexpectedStruct)

    def mustHaveArg23(self, arg2, arg3):
        self.mustHaveArg2(arg2)
        if arg3 == None:
            errorExit("Nemame arg3!", errUnexpectedStruct)

    def run(self):
        i = 0
        while i < len(RT.program):
            line = RT.program[i][0]
            # print("Processing line " + line)
            instr = RT.parser.root.findall(".//*[@order='" + line + "']")[0]
            opCode = instr.get("opcode", default="UNKNOWN")

            arg1 = instr.find("arg1")
            if arg1 == None:
                errorExit("Nemame arg1!", errUnexpectedStruct)
            arg1Text = arg1.text
            arg1Type = arg1.get("type")
            arg2 = instr.find("arg2")

            if arg2 != None:
                arg2Text = arg2.text
                arg2Type = arg2.get("type")
            else:
                arg2Text = None
                arg2Type = None
            arg3 = instr.find("arg3")
            if arg3 != None:
                arg3Text = arg3.text
                arg3Type = arg3.get("type")
            else:
                arg3Text = None
                arg3Type = None

            if opCode == "WRITE":
                if arg1Type == "var":
                    print(self.getVar(arg1Text), end="")
                elif arg1Type == "string":
                    print(self.strHexToChar(arg1Text), end="")
                else:
                    print( arg1Type + " " + arg1Text + " JESTE NEUMIM VYPSAT")
            elif opCode == "DEFVAR":
                RT.defineVar(arg1Text)
            elif opCode == "MOVE":
                self.mustHaveArg2(arg2)
                RT.setVar(arg1Text, arg2.get("type"), arg2Text)
            elif opCode == "LABEL":
                i += 1  # TODO tady vyresit co s tim
                continue
            elif opCode == "JUMPIFEQ":
                self.mustHaveArg23(arg2, arg3)
                if arg2Type == "var":
                    tmp1 = self.getVar(arg2Text)
                elif arg2Type == "string":
                    tmp1 = self.strHexToChar(arg2Text)
                else:
                    print(arg2Type + " " + arg2Text + " JESTE NEUMIM POROVNAVAT")
                    tmp1 = ""
                if arg3Type == "var":
                    tmp2 = self.getVar(arg3Text)
                elif arg3Type == "string":
                    tmp2 = self.strHexToChar(arg3Text)
                else:
                    print(arg3Type + " " + arg3Text + " JESTE NEUMIM POROVNAVAT")
                    tmp2 = ""

                if tmp1 == tmp2:
                    i = int(self.labels[arg1Text])
                    continue
            elif opCode == "CONCAT":
                self.mustHaveArg23(arg2, arg3)
                if arg1Type != "var":
                    errorExit("Argument 1 neni VAR!", errWrongOperandType)
                if arg2Type == "var":
                    tmp1 = self.getVar(arg2Text)
                elif arg2Type == "string":
                    tmp1 = self.strHexToChar(arg2Text)
                else:
                    print(arg2Type + " " + arg2Text + " JESTE NEUMIM KONKATENOVAT")
                    tmp1 = ""
                if arg3Type == "var":
                    tmp2 = self.getVar(arg3Text)
                elif arg3Type == "string":
                    tmp2 = self.strHexToChar(arg3Text)
                else:
                    print(arg3Type + " " + arg3Text + " JESTE NEUMIM KONKATENOVAT")
                    tmp2 = ""

                self.setVar(arg1Text, "string", tmp1 + tmp2)
            elif opCode == "JUMP":
                i = int(self.labels[arg1Text])
                continue
            else:
                errorExit("Neznama intrukce!", errLexSynt)

            i += 1


class XMLParser:
    def __init__(self, file_path):
        self.tree = ET.parse(file_path)
        self.root = self.tree.getroot()

    def find_element(self, element_name):
        elements = self.root.findall('.//{}'.format(element_name))
        return elements


def errorExit(message, errorNumber):
    sys.stderr.write(message + " On order number: " + str(lineNr))
    sys.exit(errorNumber)

RT = Runtime("spec_example.out")
RT.getLinesLabels()
RT.run()

import xml.etree.ElementTree as ET
import sys


# definice konstant
errLexSynt = 23

errWrongXMLFormat = 31
errUnexpectedStruct = 32

errSemantic = 52
errFrameNotExist = 55
class Frame:
    def __init__(self):
        self.dict = {}
        self.isInitialized = False

    def checkInitialized(self):
        if not self.isInitialized:
            errorExit("Ramec neexistuje", errFrameNotExist)


class Runtime:
    def __init__(self):
        self.GF = Frame()
        self.LF = Frame()
        self.TF = Frame()
        self.GF.isInitialized = True
        self.act_frame = self.GF

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
            self.act_frame.dict[self.actVarName] = value


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

# Example usage
try:
    parser = XMLParser('spec_example.out')
except ET.ParseError as e:
    errorExit("Chyba pri parsovani XML", errWrongXMLFormat)
    exit(0)

lineNr = 1
RT = Runtime()
program = []

for instr in parser.root:
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
    if opCode == "LABEL":
        program.append([instr.get("order", default=0), arg1Text])
    else:
        program.append([instr.get("order", default=0), None])

end = False
i = 0

while i < len(program):
    line = program[i][0]
    print("Processing line " + line)
    instr = parser.root.findall(".//*[@order='" + line + "']")[0]
    opCode = instr.get("opcode", default="UNKNOWN")

    arg1 = instr.find("arg1")
    if arg1 == None:
        errorExit("Nemame arg1!", errUnexpectedStruct)
    arg1Text = arg1.text

    if opCode == "WRITE":
        print(arg1Text)
    elif opCode == "DEFVAR":
        RT.defineVar(arg1Text)
    elif opCode == "MOVE":
        arg2 = instr.find("arg2")
        if arg2 == None:
            errorExit("Nemame arg2!", errUnexpectedStruct)
        arg2Text = arg2.text
        RT.setVar(arg1Text, arg2.get("type"), arg2Text)
    # elif opCode == "LABEL": TODO Rozmyslet se co s tim
    elif opCode == "JUMPIFEQ":
        print("AHOJ")
    elif opCode == "CONCAT":
        print("AHOJ")
    elif opCode == "JUMP":
        print("AHOJ")
    else:
        errorExit("Neznama intrukce!", errLexSynt)

    i += 1

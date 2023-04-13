"""
Jmeno: Ondrej Lukasek
Login: xlukas15
"""

import argparse
import os
import sys
import xml.etree.ElementTree as ET
import re
from collections import deque

# sys.stdout.reconfigure(encoding='utf-8')  # tohle spravi chybu v testech pri spatne definovanem prostredi,
# sys.stdin.reconfigure(encoding='utf-8')   # nicmene vyvolava mild errory v IDE PyCharm

# pomuze nastavit nasledujicich evnironment variables pred spustenim testu:
# set PYTHONIOENCODING=utf-8
# set PYTHONLEGACYWINDOWSSTDIO=utf-8

# definice konstant
err_prog_missing_parameter = 10
err_prog_cannot_open_input_file = 11
err_prog_cannot_open_output_file = 12

err_lex_synt = 23

err_wrong_xml_format = 31
err_unexpected_struct = 32

err_semantic = 52
err_wrong_operand_type = 53
err_getting_not_exist_var = 54
err_frame_not_exist = 55
err_missing_value = 56
err_wrong_operand_value = 57
err_wrong_string_operation = 58

err_internal_error = 99

# slovnik operacnich kodu instrukci a poctu jejich operandu
instruction_operands = {
    'MOVE': 2, 'CREATEFRAME': 0, 'PUSHFRAME': 0, 'POPFRAME': 0, 'DEFVAR': 1, 'CALL': 1, 'RETURN': 0,
    'PUSHS': 1, 'POPS': 1,
    'CLEARS': 0, 'ADDS': 0, 'SUBS': 0, 'MULS': 0, 'DIVS': 0, 'IDIVS': 0,  # STACK (FLOAT) extension
    'ADD': 3, 'SUB': 3, 'MUL': 3, 'IDIV': 3, 'LT': 3, 'GT': 3, 'EQ': 3, 'AND': 3, 'OR': 3, 'NOT': 2,
    'LTS': 0, 'GTS': 0, 'EQS': 0, 'ANDS': 0, 'ORS': 0, 'NOTS': 0,  # STACK extension
    'DIV': 3, 'INT2FLOAT': 2, 'FLOAT2INT': 2,  # FLOAT extension
    'INT2CHAR': 2, 'STRI2INT': 3,
    'INT2FLOATS': 0, 'FLOAT2INTS': 0, 'INT2CHARS': 0, 'STRI2INTS': 0,  # STACK (FLOAT) extension
    'READ': 2, 'WRITE': 1,
    'CONCAT': 3, 'STRLEN': 2, 'GETCHAR': 3, 'SETCHAR': 3,
    'TYPE': 2,
    'LABEL': 1, 'JUMP': 1, 'JUMPIFEQ': 3, 'JUMPIFNEQ': 3, 'EXIT': 1,
    'JUMPIFEQS': 1, 'JUMPIFNEQS': 1,  # STACK extension
    'DPRINT': 1, 'BREAK': 0
}

# tuple s typy operandu
types = ('int', 'bool', 'string', 'nil', 'label', 'type', 'var', 'float')

# Globalni promenna obsahujici aktualne zpravovanany Order pro vypis v instrukci error_exit mimo Runtime() objekt
act_order = 0


def error_exit(message, error_code):
    """
    Ukonci program s chybou error_code, vypise message na stderr.
    :param message: chybove hlaseni, ktere se vypise na standardni chybovy vystup
    :param error_code: cislo chyby, se kterou se ukonci provadeni programu
    :return: Zadna
    """
    global act_order  # Cislo order na kterem doslo chybe je v globalni promenne act_order
    if act_order != 0:
        sys.stderr.write(f"CHYBA {error_code} v order {act_order}: {message}\n")
    else:
        sys.stderr.write(f"CHYBA {error_code}: {message}\n")
    sys.exit(error_code)


# trida pro nacteni a zakladni kontrolu zdrojoveho XML soboru, metodou read() vrati kompletni serazeny program
class XMLReader:
    def __init__(self, input_file=None):
        self.input_file = input_file

    # vrati serazeny seznam radku programu, vcetne operandu
    # kontroluje strukturu zdrojoveho XML "rucne", protoze zvolena knihovna nepodporuje XSD nebo DTD
    def read(self):
        """
        Kontroluje kontrolu vstupniho XML a nasledne seradi instrukce.
        :return: serazeny seznam radku programu
        """
        instructions = []

        try:
            if not self.input_file:
                xml_content = sys.stdin.read()
                root = ET.fromstring(xml_content)
            else:
                tree = ET.parse(self.input_file)
                root = tree.getroot()

            if root.tag != "program":
                error_exit("Korenova znacka XML neni 'program'", err_unexpected_struct)

            if "language" not in root.attrib:
                error_exit("Chybi atribut 'langue' v korenove znacce 'program'", err_unexpected_struct)

            if root.get("language") != "IPPcode23":
                error_exit("Hodnota atributu 'langue' musi byt 'IPPcode23'", err_unexpected_struct)

            for xml_instruction in root:  # root.findall('instruction')
                if xml_instruction.tag != "instruction":
                    error_exit("Program osahuje jiny element nez jen 'instruction'", err_unexpected_struct)

                order = xml_instruction.get('order')
                opcode = xml_instruction.get('opcode')

                if order is None or opcode is None:
                    error_exit("Chybejici atribut 'order' nebo 'opcode'", err_unexpected_struct)

                try:
                    if int(order) < 1:
                        error_exit("Hodnota atributu 'order' musi byt vyssi nez 0", err_unexpected_struct)
                except ValueError:
                    error_exit("Hodnota atributu 'order' musi byt cele cislo", err_unexpected_struct)

                same_order_instructions = [instruction for instruction in instructions if instruction['order'] == int(order)]
                if same_order_instructions:
                    error_exit("Duplicitni hodnota atributu 'order'", err_unexpected_struct)

                # zalozeni struktury instrukce, zatim s prazdnymi argumenty/operandy
                instruction = {
                    'order': int(order),
                    'opcode': str(opcode).upper(),
                    'arguments': []
                }

                # kontrola jednotlivych argumentu instrukci
                for child in xml_instruction:
                    if child.tag not in {'arg1', 'arg2', 'arg3'}:
                        error_exit("Instrukce obsahuje i jiny subelement nez jen 'arg1', 'arg2' nebo 'arg3'", err_unexpected_struct)

                # nacteni arg1, arg2 a arg3 ve spravnem poradi
                for arg_nr in range(3):
                    arg = xml_instruction.find('arg'+str(arg_nr+1))
                    if arg is not None:
                        argtype = arg.get('type')
                        argval = arg.text
                        if argval is None:  # je otazka jestli pri zadne hodnote to je error nebo nulova hodnota,
                            # bereme to jako nulovou, ale u jinych typu nez string je to mozna spis error
                            if argtype == 'int':
                                argval = int(0)
                            elif argtype == 'float':
                                argval = float(0)
                            elif argtype == 'bool':
                                argval = False
                            elif argtype == 'string':
                                argval = ""
                            elif argtype == 'nil':
                                argval = int(0)
                            elif argtype == 'label':
                                argval = ""
                            elif argtype == 'type':
                                argval = ""
                        argument = {
                            'type': argtype,
                            'value': argval
                        }
                        instruction['arguments'].append(argument)
                    else:
                        break

                instructions.append(instruction)
        except (ET.ParseError, ValueError):
            error_exit("Chyba pri analyze zdrojovych XML dat", err_wrong_xml_format)

        sorted_instructions = sorted(instructions, key=lambda x: x['order'])

        return sorted_instructions


# trida pro zasobnik
class Stack:
    def __init__(self):
        self.stack = deque()

    def push(self, item):
        """
        Vlozi prvek na zasobnik.
        :param item: prvek, ktery se vlozi do zasobniku.
        """
        self.stack.append(item)

    def pop(self):
        """
        Vybere prvek ze zasobniku.
        :return: prvek z vrcholu zasobniku
        """
        if len(self.stack) == 0:
            error_exit("Nelze delat pop z prazdneho zasobniku", err_missing_value)
        return self.stack.pop()

    def clear(self):  # TODO overit si
        """
        Vymaze vsechny prvky ze zasobniku.
        :return: vyprazdneny zasobnik
        """
        self.stack.clear()

    def __repr__(self):
        return f"FrameStack(frames={self.stack})"


# trida pro jednotlive ramce
class Frame:
    def __init__(self, is_init=False):
        self.variables = {}
        self.is_initialized = is_init

    def check_initialized(self):
        """
        Funkce kontroluje, jestli je ramec inicializovany, pripadne vyvola chybu.
        """
        if not self.is_initialized:
            error_exit("Ramec neexistuje", err_frame_not_exist)

    def __repr__(self):
        return f"Frame(variables={self.variables})"


# trida pro zasobnik s ramci
class FrameStack:
    def __init__(self):
        self.frames = deque()

    def push_frame(self, frame):
        """
        Ulozi ramec na zasobnik ramcu.
        :param frame: ramec, ktery se bude ukladat na zasobnik
        """
        self.frames.append(frame)

    def pop_frame(self):  # TODO co vraci???
        """
        Vybere ramec z vrcholu zasobniku ramcu.
        :return:
        """
        return self.frames.pop()

    def is_empty(self):
        """
        Kontroluje, jestli je zasobnik ramcu prazdny.
        :return: 1 pokud je zasobnik prazdny, jinak vraci 0
        """
        return len(self.frames) == 0

    def __repr__(self):
        return f"FrameStack(frames={self.frames})"


class Runtime:
    def __init__(self, src_name, data_name):
        self.data_file = None
        if data_name is not None:
            try:
                self.data_file = open(data_name, "r")
            except IOError:
                self.data_file = None
                error_exit(f"Cannot open input data file '{data_name}'", err_prog_cannot_open_input_file)

        self.stack = Stack()
        self.call_stack = Stack()
        self.frame_stack = FrameStack()
        self.GF = Frame(True)  # GF frame is initialized from start
        self.LF = Frame()
        self.TF = Frame()
        self.program = []
        self.labels = {}
        self.return_value = 0

        try:
            self.parser = XMLReader(src_name)  # spec_example.out
        except ET.ParseError:
            error_exit("Chyba pri parsovani XML", err_wrong_xml_format)
        self.program = self.parser.read()
        self.check_program_and_fill_labels()
        self.instruction_count = {key: 0 for key in instruction_operands}
        self.instruction_exec = {key: 0 for key in instruction_operands}
        self.order_exec = {}
        self.inst_nr = 0
        self.arguments = []
        self.max_initialized_variables = 0

    def __del__(self):
        if self.data_file is not None:
            try:
                self.data_file.close()
            except IOError:
                error_exit(f"Problem closing input data file", err_prog_cannot_open_input_file)

    def check_program_and_fill_labels(self):
        """
        Kontroluje vstup programu a uklada si postupne vsechna navesti.
        :return: slovnik se vsemi ulozenymi navestimi v programu
        """
        for inst_nr in range(len(self.program)):
            instruction = self.program[inst_nr]

            try:
                if instruction_operands[instruction['opcode']] != len(instruction['arguments']):
                    error_exit("Spatny pocet operandu instrukce '"+instruction['opcode']+"'", err_unexpected_struct)
            except KeyError:
                error_exit("Nepodporovana instrukce '" + instruction['opcode'] + "'", err_unexpected_struct)
            for argument in instruction['arguments']:
                if argument['type'] not in types:
                    error_exit("Spatny typ argumentu instrukce '" + instruction['opcode'] + "' na Order " + str(instruction['order']), err_unexpected_struct)
            if instruction['opcode'] == "LABEL":
                arguments = instruction['arguments']
                if arguments:
                    if arguments[0]['value'] in self.labels:
                        error_exit("Duplicitni navesti instrukce 'LABEL'", err_semantic)
                    else:
                        self.labels[arguments[0]['value']] = inst_nr
                else:
                    error_exit("Instrukce 'LABEL' musi mit operand s navestim.", err_unexpected_struct)

    def get_frame_var(self, var_name):
        """
        Zjisti, do jakeho ramce patri promenna.
        :param var_name: jmeno promenne
        :return: vrati tuple - ramec promenne a jmeno promenne (za znakem '@')
        """
        if var_name[:3] == "GF@":
            frame = self.GF
        elif var_name[:3] == "LF@":
            frame = self.LF
        elif var_name[:3] == "TF@":
            frame = self.TF
        else:
            frame = None
            error_exit(f"Pokus o manipulaci s neexistujicim ramcem u promenne {var_name}", err_frame_not_exist)

        frame.check_initialized()
        if not var_name[3:]:
            error_exit("Spatne jmeno promenne", err_frame_not_exist)
        return tuple([frame, var_name[3:]])

    def define_var(self, var_name: str):
        """
        Definuje promennou v prislusnem ramci podle jejiho jmena.
        :param var_name: jmeno promenne
        :return: vlozi promennou do prislusneho ramce
        """
        frame, var = self.get_frame_var(var_name)
        if var in frame.variables:
            error_exit("Promenna " + var_name + " je jiz definovana!", err_semantic)
        else:
            frame.variables[var] = [None, None]

    def get_var(self, var_name):
        """
        Ziska promennou z jejiho ramce.
        :param var_name: jmenno promenne
        :return: list obsahujici typ a hodnotu promenne
        """
        frame, var = self.get_frame_var(var_name)
        if var not in frame.variables:
            error_exit("Promenna " + var_name + " neni definovana!", err_getting_not_exist_var)
        else:
            return frame.variables[var]

    def check_value(self, type, value):
        """
        Kontroluje hodnotu promenne podle jejiho typu.
        Pokud je jineho typu, pokusi se ji prevest na pozadovany typ.
        :param type: typ promenne
        :param value: hodnota promenne
        :return: hodnota promenne ve pozadovanem typu
        """
        try:
            if type == "int":
                value = int(value)
            elif type == "bool":
                if value is True or value == "true":
                    value = True
                else:
                    value = False
            elif type == "float":
                if isinstance(value, str):
                    if value[:2] == "0x" or value[:3] == "-0x" or value[:3] == "+0x":
                        value = float.fromhex(value)
                    elif "p" in value:
                        if value[:1] == "-":
                            value = float.fromhex("-0x" + value[1:])
                        else:
                            value = float.fromhex("0x"+value)
                    else:
                        value = float(value)
                else:
                    value = float(value)
            elif type == "string":
                if value is None:
                    value = ""
                value = str(self.str_esc_dec_to_char(value))
            elif type == "nil":
                value = int(0)
            elif type is None:  # tohle by se nemelo stat, ale pro jistotu
                error_exit(f"Promenna neni inicializovana '{value}'", err_missing_value)
            else:  # tohle by se take nemelo stat, ale pro jistotu
                error_exit(f"Nepodporovany typ '{type}'", err_internal_error)
        except ValueError:
            error_exit(f"Argument '{value}' nemuze byt pouzity jako typ '{type}'", err_unexpected_struct)
        return value

    def set_var(self, var_name, var_type, value):
        """
        Nastavi hodnotu promenne.
        :param var_name: jmeno promenne
        :param var_type: typ promenne
        :param value: pozadovana hodnota promenne
        """
        frame, var = self.get_frame_var(var_name)
        if var not in frame.variables:
            error_exit("Promenna " + var_name + " neni definovana!", err_getting_not_exist_var)
        else:
            value = self.check_value(var_type, value)
            frame.variables[var] = [var_type, value]

    @staticmethod
    def str_esc_dec_to_char(input_string):
        """
        Prepise decimalni escape sekvenci na znak.
        :param input_string: stupni retezec
        :return: retezec s prevedenou escape sekvenci
        """
        if input_string is None:
            return ""
        else:
            return re.sub(r'\\(\d{3})', lambda match: chr(int(match.group(1))), input_string)

    @staticmethod
    def extract_args(arguments, count):
        """
        Vybere argumenty z instrukce.
        :param arguments: argumenty instrukce
        :param count: pocet argumentu
        :return: tuple s 'count' poctem paru [typ, hodnota]
        """
        extracted = []
        try:
            for index in range(0, count):
                arg_type = arguments[index]['type']
                arg_value = arguments[index]['value']
                extracted.extend([arg_type, arg_value])
        except KeyError:
            error_exit("Argument nema typ nebo hodnotu", err_unexpected_struct)
        return tuple(extracted)

    def symbol_value(self, arg_type, arg):
        """
        Zjisti a vrati typ a hodnotu argumentu <symb>.
        :param arg_type: typ argumentu
        :param arg: argument
        :return: typ a hodnota argumentu
        """
        type = None
        value = None
        if arg_type == "var":
            type, value = self.get_var(arg)
            if type is None:
                error_exit(f"Promenna '{arg}' neni inicializovana", err_missing_value)
        else:
            type = arg_type
            value = arg
        value = self.check_value(type, value)
        return [type, value]

    def symbol_to_str(self, arg_type, arg):
        """
        Prevede hodnotu argumentu <symb> na retezec.
        :param arg_type: typ argumentu
        :param arg: argument
        :return: hodnota argumentu prevedena na retezec
        """
        value_type, value = self.symbol_value(arg_type, arg)
        if value_type == "int":
            return str(value)
        elif value_type == "bool":
            if value:
                return "true"
            else:
                return "false"
        elif value_type == "float":
            return str(value.hex())
        elif value_type == "string":
            if value is None:
                value = ""
            return str(self.str_esc_dec_to_char(value))
        elif value_type == "nil":
            return ""
        else:
            error_exit(f"Error converting argument '{arg}' with type '{arg_type}' to string", err_wrong_operand_type)

    def symbol_eq(self, arg1type, arg1value, arg2type, arg2value):
        """
        Kontroluje, jestli jsou dva argumenty <symb> ekvivalentni.
        :param arg1type: Typ prvniho argumenru.
        :param arg1value: Hodnota prvniho argumentu.
        :param arg2type: Typ druheho argumentu.
        :param arg2value: Hodnota druheho argumentu.
        :return: true pokud jsou ekvivalentni, jinak vraci false
        """
        value1_type, value1 = self.symbol_value(arg1type, arg1value)
        value2_type, value2 = self.symbol_value(arg2type, arg2value)
        if value1_type != value2_type and value1_type != "nil" and value2_type != "nil":
            error_exit("Nelze porovnavat ruzne typy operandu", err_wrong_operand_type)
        if (value1_type != "nil" and value2_type == "nil") or (value1_type == "nil" and value2_type != "nil"):
            return False
        else:
            return value1 == value2

    def check_label(self, arg_type, label):
        """
        Kontroluje spravnost instrukce LABEL.
        :param arg_type: typ argumentu
        :param label: navesti
        :return: zadny, pripadne vyvola chybu
        """
        if arg_type != "label":
            error_exit("Prvni argument instrukce skoku musi byt label", err_wrong_operand_type)
        if label not in self.labels:
            error_exit("Neexistujici navesti pro skok", err_semantic)

    def count_initialized_variables(self):
        """
        Spocita celkovy pocet incializovanych promennych v programu.
        :return: pocet incializovanych promennych
        """
        count = 0
        for frame in [self.GF, self.LF, self.TF]:
            if frame.is_initialized:
                for variable in frame.variables.values():
                    if variable[0] is not None:  # Check if the variable type is not None
                        count += 1
        if count > self.max_initialized_variables:
            self.max_initialized_variables = count
        return count

    def get_operands(self, arguments, required_operands):
        """
        Nacte operandy instrukce, zkontroluje a prevede typy.
        :param arguments: argumenty instrukce
        :param required_operands: seznam pozadovanych operandu
        :return: operandy instrukce, pokud jsou hodnoty promenne,
        tak i zkontroluje spravnost jejich typu proti pozadovanym
        """
        arg_list = self.extract_args(arguments, len(required_operands))
        if len(arg_list) != len(required_operands) * 2:
            error_exit("Chyba pri nacitani argumentu instrukce", err_unexpected_struct)  # err_internal_error ???
        operands = []
        arg_nr = 1
        for required in required_operands:
            if required == 'var':
                if arg_list[0] != "var":
                    error_exit(f"Argument {arg_nr} musi byt VAR!", err_wrong_operand_type)
                operands.extend(arg_list[:2])
            elif required == 'symb':
                value_list = self.symbol_value(arg_list[0], arg_list[1])
                operands.extend(value_list)
            elif required in ['int', 'float', 'bool', 'string']:
                value_list = self.symbol_value(arg_list[0], arg_list[1])
                if required != value_list[0]:  # kontrola spravneho typu
                    error_exit(f"Operand {arg_nr} musi byt typu '{required}'", err_wrong_operand_type)
                operands.extend(value_list)
            elif required == 'intfloat':
                value_list = self.symbol_value(arg_list[0], arg_list[1])
                if value_list[0] != 'int' and value_list[0] != 'float':
                    error_exit(f"Operand {arg_nr} musi byt typu '{required}'", err_wrong_operand_type)
                operands.extend(value_list)
            else:
                error_exit(f"Neznamy typ pozadovaneho operandu '{required}'", err_internal_error)
            arg_list = arg_list[2:]
            arg_nr += 1
        return tuple(operands)

    def get_operands_stack(self, required_operands):
        """
        Nacte operandy instrukce ze zasobniku, zkontroluje a prevede typy.
        :param required_operands: seznam pozadovanych operandu
        :return: operandy instrukce, pokud jsou hodnoty promenne,
        tak i zkontroluje spravnost jejich typu proti pozadovanym
        """
        operands = []
        arg_nr = 1
        for required in required_operands:
            arg_type, arg = self.stack.pop()
            if required == 'symb':
                value_list = self.symbol_value(arg_type, arg)
                operands.extend(value_list)
            elif required in ['int', 'float', 'bool', 'string']:
                value_list = self.symbol_value(arg_type, arg)
                if required != value_list[0]:
                    error_exit(f"Operand {arg_nr} musi byt typu '{required}'", err_wrong_operand_type)
                operands.extend(value_list)
            elif required == 'intfloat':
                value_list = self.symbol_value(arg_type, arg)
                if value_list[0] != 'int' and value_list[0] != 'float':
                    error_exit(f"Operand {arg_nr} musi byt typu '{required}'", err_wrong_operand_type)
                operands.extend(value_list)
            else:
                error_exit(f"Neznamy typ pozadovaneho operandu '{required}'", err_internal_error)
            arg_nr += 1
        return tuple(operands)

    def do_MOVE(self):
        """
        Vykona instrukci MOVE <var> <symb>.
        """
        arg1_type, arg1, value_type, value = self.get_operands(self.arguments, ('var', 'symb'))
        self.set_var(arg1, value_type, value)
        self.inst_nr += 1

    def do_CREATEFRAME(self):
        """
        Vykona instrukci CREATEFRAME.
        """
        self.TF.variables.clear()
        self.TF.is_initialized = True
        self.inst_nr += 1

    def do_PUSHFRAME(self):
        """
        Vykona instrukci PUSHFRAME.
        """
        if not self.TF.is_initialized:
            error_exit("Ramec TF neni incializovany, nelze provest PUSHFRAME", err_frame_not_exist)
        self.frame_stack.push_frame(self.TF)
        self.LF = self.TF
        self.TF = Frame()
        self.inst_nr += 1

    def do_POPFRAME(self):
        """
        Vykona instrukci POPFRAME.
        """
        if self.frame_stack.is_empty():
            error_exit("Zasobnik ramcu je prazdny, nelze provest POPFRAME", err_frame_not_exist)
        self.TF = self.frame_stack.pop_frame()
        if self.frame_stack.is_empty():
            self.LF = Frame()
        else:
            self.LF = self.frame_stack.frames[-1]
        self.inst_nr += 1

    def do_DEFVAR(self):
        """
        Vykona instrukci DEFVAR <var>.
        """
        arg_type, arg = self.get_operands(self.arguments, ['var'])
        self.define_var(arg)
        self.inst_nr += 1

    def do_CALL(self):
        """
        Vykona instrukci CALL <label>.
        """
        arg_type, arg = self.extract_args(self.arguments, 1)
        self.check_label(arg_type, arg)
        self.call_stack.push(self.inst_nr+1)
        self.inst_nr = int(self.labels[arg])

    def do_RETURN(self):
        """
        Vykona instrukci RETURN.
        """
        self.inst_nr = self.call_stack.pop()

    def do_PUSHS(self):
        """
        Vykona zasobnikovou instrukci PUSHS <symb>.
        """
        value_type, value = self.get_operands(self.arguments, ['symb'])
        self.stack.push([value_type, value])
        self.inst_nr += 1

    def do_POPS(self):
        """
        Vykona zasobnikovou instrukci POPS <var>.
        """
        arg_type, arg = self.get_operands(self.arguments, ['var'])
        value_type, value = self.stack.pop()
        self.set_var(arg, value_type, value)
        self.inst_nr += 1

    def do_CLEARS(self): # TODO zadna takova instrukce v seznamu neni
        self.stack.clear()
        self.inst_nr += 1

    def do_ADDS(self):  # TODO
        value3_type, value3, value2_type, value2 = self.get_operands_stack(['intfloat', 'intfloat'])
        if value2_type != value3_type:
            error_exit("Oba operandy instrukce ADDS musi byt stejneho typu 'int' nebo 'float'", err_wrong_operand_type)
        self.stack.push([value2_type, value2 + value3])
        self.inst_nr += 1

    def do_SUBS(self):  # TODO
        value3_type, value3, value2_type, value2 = self.get_operands_stack(['intfloat', 'intfloat'])
        if value2_type != value3_type:
            error_exit("Oba operandy instrukce SUBS musi byt stejneho typu 'int' nebo 'float'", err_wrong_operand_type)
        self.stack.push([value2_type, value2 - value3])
        self.inst_nr += 1

    def do_MULS(self):  # TODO
        value3_type, value3, value2_type, value2 = self.get_operands_stack(['intfloat', 'intfloat'])
        if value2_type != value3_type:
            error_exit("Oba operandy instrukce MULS musi byt stejneho typu 'int' nebo 'float'", err_wrong_operand_type)
        self.stack.push([value2_type, value2 * value3])
        self.inst_nr += 1

    def do_DIVS(self):  # TODO
        value3_type, value3, value2_type, value2 = self.get_operands_stack(['float', 'float'])
        if value3 == 0:
            error_exit("Nelze delit nulou", err_wrong_operand_value)
        self.stack.push(["float", value2 / value3])
        self.inst_nr += 1

    def do_IDIVS(self):  # TODO
        value3_type, value3, value2_type, value2 = self.get_operands_stack(['int', 'int'])
        if value3 == 0:
            error_exit("Nelze delit nulou", err_wrong_operand_value)
        self.stack.push(["int", value2 // value3])
        self.inst_nr += 1

    def do_ADD(self):
        """
        Vykona instrukci ADD <var> <symb1> <symb2> (soucet).
        """
        arg1_type, arg1, value2_type, value2, value3_type, value3 = self.get_operands(self.arguments, ('var', 'intfloat', 'intfloat'))
        if value2_type != value3_type:
            error_exit("Oba operandy instrukce ADD musi byt stejneho typu 'int' nebo 'float'", err_wrong_operand_type)
        self.set_var(arg1, value2_type, value2 + value3)
        self.inst_nr += 1

    def do_SUB(self):
        """
        Vykona instrukci SUB <var> <symb1> <symb2> (rozdil).
        """
        arg1_type, arg1, value2_type, value2, value3_type, value3 = self.get_operands(self.arguments, ('var', 'intfloat', 'intfloat'))
        if value2_type != value3_type:
            error_exit("Oba operandy instrukce SUB musi byt stejneho typu 'int' nebo 'float'", err_wrong_operand_type)
        self.set_var(arg1, value2_type, value2 - value3)
        self.inst_nr += 1

    def do_MUL(self):
        """
        Vykona instrukci MUL <var> <symb1> <symb2> (soucin).
        """
        arg1_type, arg1, value2_type, value2, value3_type, value3 = self.get_operands(self.arguments, ('var', 'intfloat', 'intfloat'))
        if value2_type != value3_type:
            error_exit("Oba operandy instrukce MUL musi byt stejneho typu 'int' nebo 'float'", err_wrong_operand_type)
        self.set_var(arg1, value2_type, value2 * value3)
        self.inst_nr += 1

    def do_IDIV(self):
        """
        Vykona instrukci IDIV <var> <symb1> <symb2> (celociselny podil).
        """
        arg1_type, arg1, value2_type, value2, value3_type, value3 = self.get_operands(self.arguments, ('var', 'int', 'int'))
        if value3 == 0:
            error_exit("Nelze delit nulou", err_wrong_operand_value)
        self.set_var(arg1, "int", value2 // value3)
        self.inst_nr += 1

    def do_LT(self):
        """
        Vykona instrukci LT <var> <symb1> <symb2> (mensi nez). Vysledek je typu bool.
        """
        arg1_type, arg1, value2_type, value2, value3_type, value3 = self.get_operands(self.arguments, ('var', 'symb', 'symb'))
        if value2_type != value3_type or value2_type == "nil" or value3_type == "nil":
            error_exit("Oba operandy instrukce GTS musi byt typu stejného typu a nesmi byt nil", err_wrong_operand_type)
        self.set_var(arg1, "bool", value2 < value3)
        self.inst_nr += 1

    def do_GT(self):
        """
        Vykona instrukci GT <var> <symb1> <symb2> (vetsi nez). Vysledek je typu bool.
        """
        arg1_type, arg1, value2_type, value2, value3_type, value3 = self.get_operands(self.arguments, ('var', 'symb', 'symb'))
        if value2_type != value3_type or value2_type == "nil" or value3_type == "nil":
            error_exit("Oba operandy instrukce GTS musi byt typu stejného typu a nesmi byt nil", err_wrong_operand_type)
        self.set_var(arg1, "bool", value2 > value3)
        self.inst_nr += 1

    def do_EQ(self):
        """
        Vykona instrukci EQ <var> <symb1> <symb2> (ekvivalence). Vysledek je typu bool.
        """
        arg1_type, arg1, value2_type, value2, value3_type, value3 = self.get_operands(self.arguments, ('var', 'symb', 'symb'))
        if value2_type != value3_type and value2_type != "nil" and value3_type != "nil":
            error_exit("Oba operandy instrukce EQ musi byt typu stejného typu", err_wrong_operand_type)
        if (value2_type != "nil" and value3_type == "nil") or (value2_type == "nil" and value3_type != "nil"):
            self.set_var(arg1, "bool", False)
        else:
            self.set_var(arg1, "bool", value2 == value3)
        self.inst_nr += 1

    def do_AND(self):
        """
        Vykona instrukci AND <var> <symb1> <symb2> (konjunkce). Vysledek je typu bool.
        """
        arg1_type, arg1, value2_type, value2, value3_type, value3 = self.get_operands(self.arguments, ('var', 'bool', 'bool'))
        self.set_var(arg1, "bool", value2 and value3)
        self.inst_nr += 1

    def do_OR(self):
        """
        Vykona instrukci OR <var> <symb1> <symb2> (disjunkce). Vysledek je typu bool.
        """
        arg1_type, arg1, value2_type, value2, value3_type, value3 = self.get_operands(self.arguments, ('var', 'bool', 'bool'))
        self.set_var(arg1, "bool", value2 or value3)
        self.inst_nr += 1

    def do_NOT(self):
        """
        Vykona instrukci NOT <var> <symb1> <symb2> (negace). Vysledek je typu bool.
        """
        arg1_type, arg1, value_type, value = self.get_operands(self.arguments, ('var', 'bool'))
        self.set_var(arg1, "bool", not value)
        self.inst_nr += 1

    def do_LTS(self):  # TODO
        value3_type, value3, value2_type, value2 = self.get_operands_stack(['symb', 'symb'])
        if value2_type != value3_type or value2_type == "nil" or value3_type == "nil":
            error_exit("Oba operandy instrukce GTS musi byt typu stejného typu a nesmi byt nil", err_wrong_operand_type)
        self.stack.push(["bool", value2 < value3])
        self.inst_nr += 1

    def do_GTS(self):  # TODO
        value3_type, value3, value2_type, value2 = self.get_operands_stack(['symb', 'symb'])
        if value2_type != value3_type or value2_type == "nil" or value3_type == "nil":
            error_exit("Oba operandy instrukce GTS musi byt typu stejného typu a nesmi byt nil", err_wrong_operand_type)
        self.stack.push(["bool", value2 > value3])
        self.inst_nr += 1

    def do_EQS(self):  # TODO
        value3_type, value3, value2_type, value2 = self.get_operands_stack(['symb', 'symb'])
        if value2_type != value3_type and value2_type != "nil" and value3_type != "nil":
            error_exit("Oba operandy instrukce EQS musi byt typu stejného typu", err_wrong_operand_type)
        if (value2_type != "nil" and value3_type == "nil") or (value2_type == "nil" and value3_type != "nil"):
            self.stack.push(["bool", False])
        else:
            self.stack.push(["bool", value2 == value3])
        self.inst_nr += 1

    def do_ANDS(self):  # TODO
        value3_type, value3, value2_type, value2 = self.get_operands_stack(['bool', 'bool'])
        self.stack.push(["bool", value2 and value3])
        self.inst_nr += 1

    def do_ORS(self):  # TODO
        value3_type, value3, value2_type, value2 = self.get_operands_stack(['bool', 'bool'])
        self.stack.push(["bool", value2 or value3])
        self.inst_nr += 1

    def do_NOTS(self):  # TODO
        value_type, value = self.get_operands_stack(['bool'])
        self.stack.push(["bool", not value])
        self.inst_nr += 1

    def do_DIV(self):  # TODO
        arg1_type, arg1, value2_type, value2, value3_type, value3 = self.get_operands(self.arguments, ('var', 'float', 'float'))
        if value3 == 0:
            error_exit("Nelze delit nulou", err_wrong_operand_value)
        self.set_var(arg1, "float", value2 / value3)
        self.inst_nr += 1

    def do_INT2FLOAT(self):  # TODO
        arg1_type, arg1, value_type, value = self.get_operands(self.arguments, ('var', 'int'))
        try:
            self.set_var(arg1, "float", float(value))
        except (ValueError, TypeError):
            error_exit("Vyjimka pri prevodu INT na FLOAT!", err_wrong_string_operation)
        self.inst_nr += 1

    def do_FLOAT2INT(self):  # TODO
        arg1_type, arg1, value_type, value = self.get_operands(self.arguments, ('var', 'float'))
        try:
            self.set_var(arg1, "int", int(value))
        except (ValueError, TypeError):
            error_exit("Vyjimka pri prevodu FLOAT na INT!", err_wrong_string_operation)
        self.inst_nr += 1

    def do_INT2CHAR(self):
        """
        Provede instrukci INT2CHAR <var> <symb> (prevod ciselne hodnoty na znak).
        """
        arg1_type, arg1, value_type, value = self.get_operands(self.arguments, ('var', 'int'))
        if value < 0 or value > 1114111:
            error_exit("Argument 2 musi byt INT v rozsahu 0-1114111!", err_wrong_string_operation)
        try:
            self.set_var(arg1, "string", str(chr(value)))
        except (ValueError, TypeError):
            error_exit("Vyjimka pri prevodu INT na CHAR string!", err_wrong_string_operation)
        self.inst_nr += 1

    def do_STRI2INT(self):
        """
        Provede instrukci STRI2INT <var> <symb1> <symb2> (do <var> se ulozi hodnota znaku v <symb1> na pozici <symb2>).
        """
        arg1_type, arg1, value2_type, value2, value3_type, value3 = self.get_operands(self.arguments, ('var', 'string', 'int'))
        if value3 < 0 or value3 > len(value2)-1:
            error_exit("Argument 2 musi byt INT v rozsahu 0 az delka retezce - 1!", err_wrong_string_operation)
        char_at_pos = value2[value3]
        try:
            utf8_encoded = char_at_pos.encode('utf-8')
            utf8_code = int.from_bytes(utf8_encoded, byteorder='big')
            self.set_var(arg1, "int", utf8_code)
        except (ValueError, TypeError):
            error_exit("Vyjimka pri prevodu CHAR na INT!", err_wrong_string_operation)
        self.inst_nr += 1

    def do_INT2FLOATS(self):  # TODO
        value_type, value = self.get_operands_stack(['int'])
        try:
            self.stack.push(["float", float(value)])
        except (ValueError, TypeError):
            error_exit("Vyjimka pri prevodu INT na FLOAT!", err_wrong_string_operation)
        self.inst_nr += 1

    def do_FLOAT2INTS(self):  # TODO
        value_type, value = self.get_operands_stack(['float'])
        try:
            self.stack.push(["int", int(value)])
        except (ValueError, TypeError):
            error_exit("Vyjimka pri prevodu FLOAT na INT!", err_wrong_string_operation)
        self.inst_nr += 1

    def do_INT2CHARS(self):  # TODO
        value_type, value = self.get_operands_stack(['int'])
        if value < 0 or value > 1114111:
            error_exit("Operand INT2CHARS musi byt INT v rozsahu 0-1114111!", err_wrong_string_operation)
        try:
            self.stack.push(["string", str(chr(value))])
        except (ValueError, TypeError):
            error_exit("Vyjimka pri prevodu INT na CHAR string!", err_wrong_string_operation)
        self.inst_nr += 1

    def do_STRI2INTS(self):  # TODO
        value3_type, value3, value2_type, value2 = self.get_operands_stack(['int', 'string'])  # pozor stack = operandy v opacnem poradi
        if value3 < 0 or value3 > len(value2)-1:
            error_exit("Argument 2 musi byt INT v rozsahu 0 az delka retezce - 1!", err_wrong_string_operation)
        char_at_pos = value2[value3]
        try:
            utf8_encoded = char_at_pos.encode('utf-8')
            utf8_code = int.from_bytes(utf8_encoded, byteorder='big')
            self.stack.push(["int", utf8_code])
        except (ValueError, TypeError):
            error_exit("Vyjimka pri prevodu CHAR na INT!", err_wrong_string_operation)
        self.inst_nr += 1

    def do_READ(self):
        """
        Vykona instrukci READ <var> <type> (nacteni hodnoty typu <type> ze stdin do <var>).
        """
        arg1_type, arg1, arg2_type, arg2 = self.extract_args(self.arguments, 2)
        if arg1_type != "var":
            error_exit("Argument 1 musi byt VAR!", err_wrong_operand_type)
        if arg2_type != "type":
            error_exit("Argument 2 musi byt TYPE!", err_wrong_operand_type)
        type = arg2
        if type not in ('int', 'bool', 'string', 'float'):
            error_exit("Argument 2 musi byt platny typ!", err_wrong_operand_type)
        value = None
        if self.data_file is None:
            value = input()
        else:
            try:
                value = self.data_file.readline()
                if value:
                    value = value.strip()
                else:
                    value = None
            except IOError:
                value = None
        try:
            if value is None:
                type = "nil"
                value = int(0)

            if type == "int":
                value = int(value)
            elif type == "float":
                if isinstance(value, str):
                    if value[:2] == "0x" or value[:3] == "-0x" or value[:3] == "+0x":
                        value = float.fromhex(value)
                    elif "p" in value:
                        if value[:1] == "-":
                            value = float.fromhex("-0x" + value[1:])
                        else:
                            value = float.fromhex("0x"+value)
                    else:
                        value = float(value)
                else:
                    value = float(value)
            elif type == "string":
                value = str(value)
            elif type == "bool":
                value = (str(value).upper() == "TRUE")
        except ValueError:
            type = "nil"
            value = int(0)
        self.set_var(arg1, type, value)
        self.inst_nr += 1

    def do_WRITE(self):
        """
        Vykona instrukci WRITE <symb> (vypise hodnotu <symb> na stdout).
        """
        arg_type, arg = self.extract_args(self.arguments, 1)
        print(self.symbol_to_str(arg_type, arg), end='')
        self.inst_nr += 1

    def do_CONCAT(self):
        """
        Vykona instrukci CONCAT <var> <symb1> <symb2> (konkatenace <symb1> se <symb2> a ulozeni do <var>).
        """
        arg1_type, arg1, value2_type, value2, value3_type, value3 = self.get_operands(self.arguments, ('var', 'string', 'string'))
        self.set_var(arg1, "string", value2 + value3)
        self.inst_nr += 1

    def do_STRLEN(self):
        """
        Vykona instrukci STRLEN <var> <symb> (spocita delku retezce v <symb> a ulozi ji do <var>).
        """
        arg1_type, arg1, value_type, value = self.get_operands(self.arguments, ('var', 'string'))
        try:
            self.set_var(arg1, "int", len(value))
        except (ValueError, TypeError):
            error_exit("Vyjimka pri prevodu INT na CHAR string!", err_wrong_string_operation)
        self.inst_nr += 1

    def do_GETCHAR(self):
        """
        Vykona instrukci GETCHAR <var> <symb1> <symb2> (do <var> ulozi znak ze <symb1> na pozici <symb2>).
        """
        arg1_type, arg1, value2_type, value2, value3_type, value3 = self.get_operands(self.arguments, ('var', 'string', 'int'))
        if value3 < 0 or value3 > len(value2)-1:
            error_exit("Argument 3 musi byt v rozsahu delky retece Argument 2", err_wrong_string_operation)
        self.set_var(arg1, "string", value2[value3])
        self.inst_nr += 1

    def do_SETCHAR(self):
        """
        Vykona instrukci SETCHAR <var> <symb1> <symb2> (zmeni znak retezce ve <var> na znak ze <symb1>, pozice <symb2>).
        """
        arg1_type, arg1, value2_type, value2, value3_type, value3 = self.get_operands(self.arguments, ('var', 'int', 'string'))
        value1_type, value1 = self.symbol_value(arg1_type, arg1)
        if value1_type != "string":
            error_exit("Promenna Argument 1 musi byt typu 'string'", err_wrong_operand_type)
        if value2 < 0 or value2 > len(value1)-1:
            error_exit("Argument 2 musi byt v rozsahu delky retece Argument 1", err_wrong_string_operation)
        if len(value3) == 0:
            error_exit("Argument 3 nesmi byt prazdny retezec", err_wrong_string_operation)
        value1 = value1[:value2] + value3[0] + value1[value2 + 1:]
        self.set_var(arg1, "string", value1)
        self.inst_nr += 1

    def do_TYPE(self):
        """
        Vykona instrukci TYPE <var> <symb> (do <var> ulozi typ <symb> formou retezce).
        """
        arg1_type, arg1, arg2_type, arg2 = self.extract_args(self.arguments, 2)
        if arg1_type != "var":
            error_exit("Argument 1 musi byt VAR!", err_wrong_operand_type)
        type = None
        value = None
        if arg2_type == "var":
            type, value = self.get_var(arg2)
            if type is None:
                type = ""
        else:
            type = arg2_type
            value = arg2
        self.set_var(arg1, "string", type)
        self.inst_nr += 1

    def do_LABEL(self):
        """
        Instrukce LABEL <label>. Vytvori v programu cil <label>, na ktery provest skok skokove instrukce.
        """
        self.inst_nr += 1

    def do_JUMP(self):
        """
        Vykona instrukci JUMP <label>. Provede nepodmineny skok na navesti
        """
        arg_type, arg = self.extract_args(self.arguments, 1)
        self.check_label(arg_type, arg)
        self.inst_nr = int(self.labels[arg])

    def do_JUMPIFEQ(self):
        """
        Vykona instrukci JUMPIFEQ <label> <symb1> <symb2>. Provede skok na navesti label,
        pokud jsou si <symb1> a <symb2> rovny.
        """
        arg1_type, arg1, arg2_type, arg2, arg3_type, arg3 = self.extract_args(self.arguments, 3)
        self.check_label(arg1_type, arg1)
        if self.symbol_eq(arg2_type, arg2, arg3_type, arg3):
            self.inst_nr = int(self.labels[arg1])
        else:
            self.inst_nr += 1

    def do_JUMPIFNEQ(self):
        """
        Vykona instrukci JUMPIFNEQ <label> <symb1> <symb2>. Provede skok na navesti label,
        pokud si hodnoty <symb1> a <symb2> nejsou rovny.
        """
        arg1_type, arg1, arg2_type, arg2, arg3_type, arg3 = self.extract_args(self.arguments, 3)
        self.check_label(arg1_type, arg1)
        if not self.symbol_eq(arg2_type, arg2, arg3_type, arg3):
            self.inst_nr = int(self.labels[arg1])
        else:
            self.inst_nr += 1

    def do_EXIT(self):
        """
        Provede instrukci EXIT <symb>. Ukonci vykonavani programu s navratovym kodem <symb>.
        """
        value_type, value = self.get_operands(self.arguments, ['int'])
        try:
            if 0 <= int(value) <= 49:
                self.return_value = value  # pripravime navratovou hodnotu
                # sys.exit(int(value))
                self.inst_nr = len(self.program)  # a skocime na radek za program (konec)
            else:
                error_exit("Navratova hodnota funkce EXIT musi byt cele cislo 0-49", err_wrong_operand_value)
        except ValueError:
            error_exit("Navratova hodnota funkce EXIT musi byt cele cislo 0-49", err_wrong_operand_value)

    def do_JUMPIFEQS(self):  # TODO
        arg_type, arg = self.extract_args(self.arguments, 1)
        self.check_label(arg_type, arg)
        arg3_type, arg3 = self.stack.pop()
        arg2_type, arg2 = self.stack.pop()
        if self.symbol_eq(arg2_type, arg2, arg3_type, arg3):
            self.inst_nr = int(self.labels[arg])
        else:
            self.inst_nr += 1

    def do_JUMPIFNEQS(self):  # TODO
        arg_type, arg = self.extract_args(self.arguments, 1)
        self.check_label(arg_type, arg)
        arg3_type, arg3 = self.stack.pop()
        arg2_type, arg2 = self.stack.pop()
        if not self.symbol_eq(arg2_type, arg2, arg3_type, arg3):
            self.inst_nr = int(self.labels[arg])
        else:
            self.inst_nr += 1

    def do_DPRINT(self):
        """
        Provede instrukci DPRINT <symb>. Vypise <symb> na stderr.
        """
        arg_type, arg = self.extract_args(self.arguments, 1)
        sys.stderr.write(self.symbol_to_str(arg_type, arg))
        self.inst_nr += 1

    def do_BREAK(self):
        """
        Provede instrukci BREAK. Vypise stav interpretu na stderr (napr pozice v kodu, obsah ramcu, ...) v dobe
        vykonavani teto instrukce.
        """
        instruction = self.program[self.inst_nr]
        sys.stderr.write(f"Vykonavam instukci: {instruction}\n")
        sys.stderr.write(f"GF frame: {self.GF} {self.GF.is_initialized}\n")
        sys.stderr.write(f"LF frame: {self.LF} {self.LF.is_initialized}\n")
        sys.stderr.write(f"TF frame: {self.TF} {self.TF.is_initialized}\n")
        instructions = sum(self.instruction_exec.values())
        sys.stderr.write(f"Celkem vykonanych instrukci: {instructions}\n")
        self.inst_nr += 1

    def run(self):  # TODO
        global act_order  # Cislo order ktery se zpracovava je v globalni promenne act_order, tam ho budeme menit

        for instruction in self.program:
            self.instruction_count[instruction['opcode']] += 1

        keywords = list(instruction_operands.keys())

        function_map = {keyword: getattr(self, f"do_{keyword}") for keyword in keywords}

        while self.inst_nr < len(self.program):
            instruction = self.program[self.inst_nr]
            act_order = instruction['order']
            opcode = instruction['opcode']
            self.arguments = instruction['arguments']

            # Uprava pocitadel do statistik
            self.instruction_exec[opcode] += 1
            self.order_exec[instruction['order']] = self.order_exec.get(instruction['order'], 0) + 1

            # Volani dopovidajicich funkci podle jmena instrukce
            if opcode in function_map:
                function_map[opcode]()  # Vola do_OPCODE()
            else:
                error_exit(f"Neznama intrukce '{opcode}'!", err_lex_synt)

            # Spocitani incicializovanych promennych ve vsech ramcich
            self.count_initialized_variables()


def write_stats_file(stats_file, runtime):  # TODO
    for arg in sys.argv:
        # print( arg[:5] )
        if arg[:7] == '--insts':
            instructions = sum(runtime.instruction_exec.values())
            # stats_file.write(f"{instructions}\n")
            instructions -= runtime.instruction_exec['LABEL']
            instructions -= runtime.instruction_exec['DPRINT']
            instructions -= runtime.instruction_exec['BREAK']
            stats_file.write(f"{instructions}\n")
        elif arg[:5] == '--hot':
            max_exec = max(runtime.instruction_exec.values())
            max_exec_instructions = [(instruction, count) for instruction, count in runtime.instruction_exec.items() if count == max_exec]
            # print("Instructions with the highest count:", max_exec_instructions)
            max_count_opcodes = {instruction for instruction, _ in max_exec_instructions}
            max_count_opcodes.discard('LABEL')  # otazka je, jestli tyto take oddelavat?
            max_count_opcodes.discard('DPRINT')
            max_count_opcodes.discard('BREAK')
            # print(max_count_opcodes)
            max_exec_opcode_orders = []
            for instr in runtime.program:
                if instr['opcode'] in max_count_opcodes:
                    max_exec_opcode_orders.append(instr['order'])
                    # print(f"Order of {instr['opcode']}: {instr['order']}")
            # print("minumum:", min(max_exec_opcode_orders))
            stats_file.write(f"{min(max_exec_opcode_orders)}\n")
        elif arg[:6] == '--vars':
            stats_file.write(f"{runtime.max_initialized_variables}\n")
        elif arg[:10] == '--frequent':
            sorted_opcodes = sorted(runtime.instruction_count.items(), key=lambda item: item[1], reverse=True)
            # print(sorted_opcodes[:3])
            opcode_names = [opcode for opcode, _ in sorted_opcodes[:3]]
            output = ','.join(opcode_names)
            stats_file.write(f"{output}\n")
        elif arg[:7] == '--print':
            stats_file.write(arg[8:])
        elif arg[:7] == '--eol':
            stats_file.write('\n')


def show_help():
    """
    Zobrazi pomocne informace k pouziti skriptu.
    """
    print("Pouziti: python interpret.py [VOLBY]")
    print("Volby:")
    print("  --help         Ukaze tuto napovedu a skonci")
    print("  --source=file  Specifikace zdrojoveho XML (nebo stdin)")
    print("  --input=file   Specifikace vstupniho souboru (nebo stdin)")
    print("  --stats=file   Specifikace souboru se statistikami")
    print("    --insts      (Volitelne) Vypise pocet vykonatelnych instrukci")
    print("    --hot        (Volitelne) Vypise hodnotu order u nejcasteji vykonane instrukce")
    print("    --vars       (Volitelne) Vypise maximalni pocet promennych inicializovanych v jeden okamzik")
    print("    --frequent   (Volitelne) Vypise jmena operacnich kodu, ktere jsou ve zdrojovem kodu nejcastejsi")
    print("    --print=string (Volitelne) Vypise zadany string")
    print("    --eol        (Volitelne) Vypise odradkovani")


def main(args):  # TODO
    if args.help:
        show_help()
        return

    if not args.source and not args.input:
        print("Musi byt specifikovany minimalne jeden  parametru --source nebo --input.")
        show_help()
        return

    if args.source:
        source_file = args.source
        if not os.path.exists(source_file):
            error_exit(f"Zdrojovy XML soubor '{source_file}' nebyl nalezen.", err_prog_cannot_open_input_file)
    else:
        source_file = None

    if args.input:
        input_file = args.input
        if not os.path.exists(input_file):
            error_exit(f"Vstupni soubor '{input_file}' nebyl nalezen.", err_prog_cannot_open_input_file)
    else:
        input_file = None

    stats_file = None
    if args.stats:
        stats_file_name = args.stats
        try:
            stats_file = open(stats_file_name, 'w')
        except OSError as e:
            error_exit(f"Chyba {e} pri vytvareni souboru pro ulozeni statistik '{stats_file_name}'.", err_prog_cannot_open_output_file)
    else:
        if args.insts or args.hot or args.vars or args.frequent or args.print or args.eol:
            error_exit("Byl zadan nektery z parametru volitelnych statistik, ale bez uvodniho parametru --stats.", err_prog_missing_parameter)

    runtime = Runtime(source_file, input_file)
    runtime.run()

    if args.stats:
        write_stats_file(stats_file, runtime)
        try:
            stats_file.close()
        except OSError as e:
            error_exit(f"Chyba {e} pri uzavirani souboru se statistikami '{stats_file}'.", err_prog_cannot_open_output_file)

    return runtime.return_value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--help', action='store_true', help='Vypise tuto napovedu a skonci')
    parser.add_argument('--source', type=str, help='Ucruje zdrojovy XML soubor')
    parser.add_argument('--input', type=str, help='Urcuje soubor se vstupnimi daty')
    parser.add_argument('--stats', type=str, help='Urcuje soubor se statistikami')
    parser.add_argument('--insts', action='store_true', help='(Volitelne) Vypise pocet vykonatelnych instrukci')
    parser.add_argument('--hot', action='store_true', help='(Volitelne) Vypise hodnotu order u nejcasteji vykonane instrukce')
    parser.add_argument('--vars', action='store_true', help='(Volitelne) Vypise maximalni pocet promennych inicializovanych v jeden okamzik')
    parser.add_argument('--frequent', action='store_true', help='(Volitelne) Vypise jmena operacnich kodu, ktere jsou ve zdrojovem kodu nejcastejsi')
    parser.add_argument('--print', type=str, help='(Volitelne) Vypise zadany retezec')
    parser.add_argument('--eol', action='store_true', help='(Volitelne) Vypise odradkovani')
    prg_args = parser.parse_args()
    return_value = main(prg_args)
    sys.exit(return_value)

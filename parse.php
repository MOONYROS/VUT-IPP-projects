<?php
ini_set('display_errors', 'stderr');

define("FILENAME", "parse-only/simple_tag.src", false);
define("OUTPUT", "out.xml", false);

# NAVRATY STEJNE PRO OBA SKRIPTY
define("PROCESS_OK", 0, false);
define("PARAM_ERROR", 10, false);
define("INPUT_ERROR", 11, false);
define("OUTPUT_ERROR", 12, false);
define("INTERNAL_ERROR", 99, false);

# NAVRATY DEFINOVANE PRO parse.php
define("HEADER_ERROR", 21, false);
define("UNKNOWN_OPCODE", 22, false);
define("ERROR_LEX_SYNT", 23, false);

define("PRINT_ENABLE", 0, false);

function myPrint($text)
{
    if(PRINT_ENABLE)
        echo "LOG: $text\n";
}

function displayHelp()
{
    echo "=== NAPOVEDA KE SKRIPTU parse.php ===\n";
    echo "Skript nacita zdrojovy kod v jazyce IPPcode23, zkontroluje jeho lexikalni a syntaktickou spravnost.\n";
    echo "Pokud ve kodu nebyla chyba, prepise jej na standardni vystup ve formatu XML.\n";
    echo "Pro spusteni skriptu pouzijte nasledujici prikaz:\n";
    echo "php8.1 parse.php [volitelny parametr] <[vstupni soubor] >[vystupni soubor]\n";
}

function instructionXML($xml, $order, $lineElements)
{
    $xml->startElement("instruction");
    $xml->writeAttribute("order", $order);
    $xml->writeAttribute("opcode", $lineElements[0]);
}

function operandXML($xml, $arg, $pos, $type)
{
    $xml->startElement("arg".$pos);
    $xml->writeAttribute("type", $type);
    $xml->text($arg[$pos]);
    $xml->endElement();
}

function errorExit($exitText, $errorNumber)
{
    fprintf(STDERR, "%s", $exitText);
    exit($errorNumber);
}

function checkArguments($argc, $argv)
{
    if($argc > 1)
    {
        if(($argc == 2) && ($argv[1] == "--help"))
        {
            displayHelp();
            exit(PROCESS_OK);
        }
        else
            errorExit("SPATNE ZADANY PARAMETR!\n", PARAM_ERROR);
    }
}

function checkHeader($lineElements)
{
    if(count($lineElements) == 1) # v hlavicce ocekavame pouze jeden prvek
    {
        if(strtolower($lineElements[0]) != ".ippcode23") # nezalezi na velikosti pismen
            errorExit("Spatna hlavicka programu! Spatne zadany identifikator jazyka.\n", HEADER_ERROR);
    }
    else
        errorExit("Spatna hlavicka programu! Uvodni radek musi obsahovat pouze identifikator jazyka.\n", HEADER_ERROR);
}

function matchVar($xml, $arg, $pos)
{
    if(preg_match("/^(GF|LF|TF)@[a-zA-Z_\-$&%*!?][\w\-$&%*!?]*$/", $arg[$pos]))
        operandXML($xml, $arg, $pos, "var");
    else
        errorExit("Spatne zadany operand promenne.", ERROR_LEX_SYNT);
}
function matchLabel($xml, $arg, $pos)
{
    if(preg_match("/^[a-zA-Z_\-$&%*!?][\w\-$&%*!?]*$/", $arg[$pos]))
        operandXML($xml, $arg, $pos, "label");
    else
        errorExit("Spatne zadany operand navesti.", ERROR_LEX_SYNT);
}

function matchType($xml, $arg, $pos)
{
    if(preg_match("/int|bool|string|nil/", $arg[$pos]))
        operandXML($xml, $arg, $pos, "type");
    else
        errorExit("Spatne zadany operand typu.", ERROR_LEX_SYNT);
}

function matchConst($xml, $arg, $pos)
{
    $tokens = explode("@", $arg[$pos]);
    if(count($tokens) != 2)
        errorExit("Spatne zadana konstanta. Neobsahuje oddelovaci @.", ERROR_LEX_SYNT);

    switch($tokens[0])
    {
        case "nil":
            if($arg[$pos] != "nil@nil")
                errorExit("Spatne zadany typ nil (polozka za @).", ERROR_LEX_SYNT);
            break;
        case "int":
            if(!preg_match("/^int@(-|\+)?\d+$/", $arg[$pos]))
                errorExit("Spatne zadany typ int (polozka za @).", ERROR_LEX_SYNT);
            break;
        case "bool":
            if(!preg_match("/^bool@(true|false)$/", $arg[$pos]))
                errorExit("Spatne zadany typ bool (polozka za @).", ERROR_LEX_SYNT);
            break;
        case "string":
            if(!preg_match("/^string@[^\s]+$/", $arg[$pos])) # TODO upravit nejakym zpusobem escape sekvence
                errorExit("Spatne zadany typ string (polozka za @).", ERROR_LEX_SYNT);
            break;
        default:
            errorExit("Nerozpoznany typ konstanty. Povolene typy jsou nil, bool, int, string.", ERROR_LEX_SYNT);
            break;
    }
    # operandXML($xml, $tokens[1], $pos, $tokens[0]);
    $xml->startElement("arg".$pos);
    $xml->writeAttribute("type", $tokens[0]);
    $xml->text($tokens[1]);
    $xml->endElement();
}

function matchSymb($xml, $arg, $pos)
{
    $tokens = explode("@", $arg[$pos], 2);
    if(count($tokens) == 2)
    {
        if(($tokens[0] == "GF") || ($tokens[0] == "LF") || ($tokens[0] == "TF"))
            matchVar($xml, $arg, $pos);
        else
            matchConst($xml, $arg, $pos);
    }
    else
        errorExit("Symbol neni konstanta ani promenna.", ERROR_LEX_SYNT);
}

function checkOperands($array, $number, $message)
{
    if(count($array) != $number)
        errorExit("Spatny pocet operandu! $message\n", ERROR_LEX_SYNT);
}

####################### PSEUDOMAIN #######################

myPrint("START SKRIPTU parse.php");

checkArguments($argc, $argv);

$xml = new XMLWriter();
$xml->openMemory();
$xml->startDocument('1.0', 'UTF-8');
$xml->setIndent(true);
$xml->startElement('program');
$xml->writeAttribute('language', 'IPPcode23');

$order = 0;
$headerOK = false;
$lines = file("php://stdin"); # FILENAME
if(!$lines)
    errorExit("NEPODARILO SE PRECIST DATA\n", INPUT_ERROR);

myPrint("SOUBOR NACTEN");

for($i = 0; $i < count($lines); $i++)
{
    myPrint("RADEK $i: $lines[$i]");

    $lines[$i] = preg_replace("/#.*/", "", $lines[$i]); # odstraneni komentare
    $lines[$i] = trim($lines[$i]); # odstraneni bilych znaku od zacatku a konce radku

    if($lines[$i] != "") # kontrola, jestli neni radek prazdny, protoze z kazdeho radku odstranujeme komentare a whitespaces
    {
        $lineElements = preg_split("/\s+/", $lines[$i]); # rozdelim radek na na elementy podle bilych znaku

        # kontrola vstupu
        if(!$headerOK) # kontrola hlavicky .IPPcode23 a jine varianty
        {
            checkHeader($lineElements);
            $headerOK = true;
            myPrint("HEADER OK");
        }
        else
        {
            $order++;

            switch(strtoupper($lineElements[0]))
            {
                # INSTRUKCE S <var> <symb1> <symb2>
                case "ADD":
                case "SUB":
                case "MUL":
                case "IDIV":
                case "LT":
                case "GT":
                case "EQ":
                case "AND":
                case "OR":
                case "STRI2INT":
                case "CONCAT":
                case "GETCHAR":
                case "SETCHAR":
                    myPrint("var symb1 symb2");
                    checkOperands($lineElements, 4, "Ocekavaji se 3 operandy za instrukci.");
                    instructionXML($xml, $order, $lineElements);
                    matchVar($xml, $lineElements, 1);
                    matchSymb($xml, $lineElements, 2);
                    matchSymb($xml, $lineElements, 3);
                    break;
                # INSTRUKCE BEZ OPERANDU
                case "CREATEFRAME":
                case "PUSHFRAME":
                case "POPFRAME":
                case "RETURN":
                case "BREAK":
                    myPrint("*nema argumenty*");
                    checkOperands($lineElements, 1, "Neocekava se zadny operand.");
                    instructionXML($xml, $order, $lineElements);
                    break;
                # INSTRUKCE S <var> <symb>
                case "NOT": # ma pouze 2 operandy - do <var> nahraje <symb> jako bool (viz zadani)
                case "MOVE":
                case "INT2CHAR":
                case "STRLEN":
                case "TYPE":
                    myPrint("var symb");
                    checkOperands($lineElements, 3, "Ocekavaji se 2 operandy.");
                    instructionXML($xml, $order, $lineElements);
                    matchVar($xml, $lineElements, 1);
                    matchSymb($xml, $lineElements, 2);
                    break;
                # INSTRUKCE S <symb>
                case "PUSHS":
                case "WRITE":
                case "EXIT":
                case "DPRINT":
                    myPrint("symb");
                    checkOperands($lineElements, 2, "Ocekava se 1 operand.");
                    instructionXML($xml, $order, $lineElements);
                    matchSymb($xml, $lineElements, 1);
                    break;
                # INSTRUKCE S <label>
                case "CALL":
                case "LABEL":
                case "JUMP":
                    myPrint("label");
                    checkOperands($lineElements, 2, "Ocekava se 1 operand.");
                    instructionXML($xml, $order, $lineElements);
                    matchLabel($xml, $lineElements, 1);
                    break;
                # INSTRUKCE S <var>
                case "DEFVAR":
                case "POPS":
                    myPrint("var");
                    checkOperands($lineElements, 2, "Ocekava se 1 operand.");
                    instructionXML($xml, $order, $lineElements);
                    matchVar($xml, $lineElements, 1);
                    break;
                # INSTRUKCE S <label> <symb1> <symb2>
                case "JUMPIFEQ":
                case "JUMPIFNEQ":
                    myPrint("label symb1 symb2");
                    checkOperands($lineElements, 4, "Ocekavaji se 3 operandy.");
                    instructionXML($xml, $order, $lineElements);
                    matchLabel($xml, $lineElements, 1);
                    matchSymb($xml, $lineElements, 2);
                    matchSymb($xml, $lineElements, 3);
                    break;
                # INSTRUKCE S <var> <type>
                case "READ":
                    myPrint("var type");
                    checkOperands($lineElements, 3, "Ocekavaji se 2 operandy.");
                    instructionXML($xml, $order, $lineElements);
                    matchVar($xml, $lineElements, 1);
                    matchType($xml, $lineElements, 2);
                    break;
                # NEEXISTUJICI INSTRUKCE
                default:
                    errorExit("NEROZPOZNANA INSTRUKCE: $lineElements[0]\n", UNKNOWN_OPCODE);
                    break;
            }
            $xml->endElement();
        }
    }
}

$xml->endElement();
$xml->endDocument();
if(!file_put_contents("php://output", trim($xml->outputMemory()))) # OUTPUT
    errorExit("Nepodarilo se vypsat data.", OUTPUT_ERROR);
$xml->flush();
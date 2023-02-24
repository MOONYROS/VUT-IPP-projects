<?php
ini_set('display_errors', 'stderr');

const INPUT = "php://stdin";
const OUTPUT = "php://output";

# NAVRATY STEJNE PRO OBA SKRIPTY
const PROCESS_OK = 0;
const PARAM_ERROR = 10;
const INPUT_ERROR = 11;
const OUTPUT_ERROR = 12;

# NAVRATY DEFINOVANE PRO parse.php
const HEADER_ERROR = 21;
const UNKNOWN_OPCODE = 22;
const ERROR_LEX_SYNT = 23;

# POMOCNA KONSTANTA
const PRINT_ENABLE = 0;

/**
 * @brief Pomocna funkce, ktera funguje je jako echo, ale lze ji vypnout prepnutim konstanty PRINT_ENABLE na 0.
 * @param string $text Text, ktery bude vypsan na standardni vystup.
 * @return void Vypise zpravu na standardni vystup.
 */
function myPrint(string $text)
{
    if(PRINT_ENABLE)
        echo "LOG: $text\n";
}

/**
 * @brief Funkce pro vypis napovedy pro pouziti skriptu na standardni vystup.
 * @return void vypise napovedu ke skriptu na standartni vystup pri zadani prepinace --help
 */
function displayHelp()
{
    echo "=== NAPOVEDA KE SKRIPTU parse.php ===\n";
    echo "Skript nacita zdrojovy kod v jazyce IPPcode23, zkontroluje jeho lexikalni a syntaktickou spravnost.\n";
    echo "Pokud ve kodu nebyla chyba, prepise jej na standardni vystup ve formatu XML.\n";
    echo "Pro spusteni skriptu pouzijte nasledujici prikaz:\n";
    echo "php8.1 parse.php [volitelny parametr] <[vstupni soubor] >[vystupni soubor]\n";
}

/**
 * @brief Funkce zapise instrukci do formatu xml.
 * @param XMLWriter $xml XML soubor.
 * @param int $order Poradi instrukce.
 * @param array $lineElements Pole prvku instrukce.
 * @return void Zapisuje instrukci do formatu XML.
 */
function instructionXML(XMLWriter $xml, int $order, array $lineElements)
{
    $xml->startElement("instruction");
    $xml->writeAttribute("order", $order);
    $xml->writeAttribute("opcode", strtoupper($lineElements[0]));
}

/**
 * @brief Zapise argument do formatu XML a ocisluje jeho pozici na zaklade $arg.
 * @param XMLWriter $xml XML soubor.
 * @param array $arg Pole s argumenty instrukce.
 * @param int $pos Pozice argumentu instrukce v poli $arg.
 * @param string $type Typ operandu.
 * @return void Zapise operand do XML formatu.
 */
function operandXML(XMLWriter $xml, array $arg, int $pos, string $type)
{
    $xml->startElement("arg".$pos);
    $xml->writeAttribute("type", $type);
    $xml->text($arg[$pos]);
    $xml->endElement();
}

/**
 * @brief Vola na chybovy vystup zpravu a vraci chybovy navratovy kod podle specifikace.
 * @param string $exitText Text, ktery se navrati s chybou.
 * @param int $errorNumber Cislo, oznacujici prislusnou chybu.
 * @return void Navraci chybu zvoleneho cisla se zpravou na STDERR.
 */
function errorExit(string $exitText, int $errorNumber)
{
    fprintf(STDERR, "%s", $exitText);
    exit($errorNumber);
}

/**
 * @brief Kontroluje argumenty, jestli je spravne zapsany jejich pocet a format (jediny pripustny je --help).
 * @param int $argc Pocet argumentu.
 * @param array $argv Pole s argumenty.
 * @return void Program pokracuje (vraci 0) nebo se zahlasi chyba.
 */
function checkArguments(int $argc, array $argv)
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

/**
 * @brief Kotroluje hlavicku standardniho vstupu, na ktere musi byt napsano .IPPcode23 case insensitive.
 * @param array $lineElements Pole prvku instrukce.
 * @return void Nevraci nic, pokud je prubeh v poradku, jinak hlasi chybu.
 */
function checkHeader(array $lineElements)
{
    if(count($lineElements) == 1) # v hlavicce ocekavame pouze jeden prvek
    {
        if(strtolower($lineElements[0]) != ".ippcode23") # nezalezi na velikosti pismen
            errorExit("Spatna hlavicka programu! Spatne zadany identifikator jazyka.\n", HEADER_ERROR);
    }
    else
        errorExit("Spatna hlavicka programu! Uvodni radek musi obsahovat pouze identifikator jazyka.\n", HEADER_ERROR);
}

/**
 * @brief Kontroluje, zda je ve spravnem formatu zapsana promenna, pokud ano, zapise ji do XML, jinak vraci prislusnou chybu.
 * @param XMLWriter $xml XML soubor.
 * @param array $arg Pole s argumenty instrukce.
 * @param int $pos Pozice argumentu v poli $arg.
 * @return void Zapisuje promennou do XML formatu nebo hlasi chybu.
 */
function matchVar(XMLWriter $xml, array $arg, int $pos)
{
    if(preg_match("/^(GF|LF|TF)@[a-zA-Z_\-$&%*!?][\w\-$&%*!?]*$/", $arg[$pos]))
        operandXML($xml, $arg, $pos, "var");
    else
        errorExit("Spatne zadany operand promenne.", ERROR_LEX_SYNT);
}

/**
 * @brief Kontroluje, zda je spravne zadano navesti, pokud ano, zapise jej do XML formatu, jinak vraci prislusnou chybu.
 * @param XMLWriter $xml XML soubor.
 * @param array $arg Pole s argumenty instrukce.
 * @param int $pos Pozice argumentu v poli $arg.
 * @return void Zapisuje navesti do XML formatu nebo hlasi chybu.
 */
function matchLabel(XMLWriter $xml, array $arg, int $pos)
{
    if(preg_match("/^[a-zA-Z_\-$&%*!?][\w\-$&%*!?]*$/", $arg[$pos]))
        operandXML($xml, $arg, $pos, "label");
    else
        errorExit("Spatne zadany operand navesti.", ERROR_LEX_SYNT);
}

/**
 * @brief Kontroluje spravnost zapisu typu, pokud ano, zapise ji do formatu XML, jinak vraci prislusnou chybu.
 * @param XMLWriter $xml XML soubor.
 * @param array $arg Pole s argumenty instrukce.
 * @param int $pos Pozice daneho argumentu.
 * @return void Zapisuje typ do XML formatu nebo zahlasi chybu.
 */
function matchType(XMLWriter $xml, array $arg, int $pos)
{
    if(preg_match("/^(int|bool|string)$/", $arg[$pos]))
        operandXML($xml, $arg, $pos, "type");
    else
        errorExit("Spatne zadany operand typu.", ERROR_LEX_SYNT);
}

/**
 * @brief Kontroluje spravnost zapisu konstanty. Pokud je zadana spravne, zapise ji do XML, jinak vraci prislusnou chybu.
 * @param XMLWriter $xml XML soubor.
 * @param array $arg Pole s argumenty instrukce.
 * @param int $pos Pozice argumentu v poli.
 * @return void Zapise konstantu do XML nebo hlasi chybu.
 */
function matchConst(XMLWriter $xml, array $arg, int $pos)
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
            if(!preg_match("/^int@[+-]?\d+$/", $arg[$pos]))
                errorExit("Spatne zadany typ int (polozka za @).", ERROR_LEX_SYNT);
            break;
        case "bool":
            if(!preg_match("/^bool@(true|false)$/", $arg[$pos]))
                errorExit("Spatne zadany typ bool (polozka za @).", ERROR_LEX_SYNT);
            break;
        case "string":
            if(!preg_match("/^string@([^\s#\\\\]|\\\\\d{3})*$/", $arg[$pos]))
                errorExit("Spatne zadany typ string (polozka za @).", ERROR_LEX_SYNT);
            break;
        default:
            errorExit("Nerozpoznany typ konstanty. Povolene typy jsou nil, bool, int, string.", ERROR_LEX_SYNT);
            break;
    }
    $xml->startElement("arg".$pos);
    $xml->writeAttribute("type", $tokens[0]);
    $xml->text($tokens[1]);
    $xml->endElement();
}

/**
 * @brief Kontroluje spravnost zapisu symbolu. Pokud je symbol zadan spravne, je zapsan do XML, jinak se vraci prislusna chyba.
 * @param XMLWriter $xml XML soubor.
 * @param array $arg Pole s argumenty instrukce.
 * @param int $pos Pozice argumentu.
 * @return void Vraci chybu nebo zapise symbol do xml formatu.
 */
function matchSymb(XMLWriter $xml, array $arg, int $pos)
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

/**
 * @brief Funkce kontroluje pocet operandu u instrukci. Pokud neni pocet operandu spravny, vypisuje chybu.
 * @param array $array
 * @param int $number
 * @param string $message
 * @return void
 */
function checkOperands(array $array, int $number, string $message)
{
    if(count($array) != $number)
        errorExit("Spatny pocet operandu! $message\n", ERROR_LEX_SYNT);
}

####################### HLAVNI BEH PROGRAMU #######################

myPrint("START SKRIPTU parse.php");

# Nejdrive se pri startu spusti kontrola argumentu.
checkArguments($argc, $argv);

# pri startu programu se vytvori XMLWriter promenna.
$xml = new XMLWriter();
$xml->openMemory();
$xml->startDocument('1.0', 'UTF-8');
$xml->setIndent(true);
$xml->startElement('program');
$xml->writeAttribute('language', 'IPPcode23');

$order = 0;
$headerOK = false;
$lines = file(INPUT);
if(!$lines)
    errorExit("NEPODARILO SE PRECIST DATA\n", INPUT_ERROR);

myPrint("SOUBOR NACTEN");

# ZACATEK HLAVNIHO CYKLU PROGRAMU
for($i = 0; $i < count($lines); $i++) # kontrola vsech radku vstupniho souboru
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
            switch(strtoupper($lineElements[0])) # switch pro rozpoznavani instrukce
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
            $xml->endElement(); # konec zapisovani jedne instrukce a jejich operandu do XML formatu
        }
    }
}

$xml->endElement(); # ukonceni elementu <program>
$xml->endDocument(); # zavreni XML dokumentu
if(!file_put_contents(OUTPUT, trim($xml->outputMemory())))
    errorExit("Nepodarilo se vypsat data.", OUTPUT_ERROR);
$xml->flush(); # vraceni XML bufferu

<?php

define("FILENAME", "parse-only/write_test.src", false);

# NAVRATY STEJNE PRO OBA SKRIPTY
define("PROCCESS_OK", 0, false);
define("PARAM_ERROR", 10, false);
define("INPUT_ERROR", 11, false);
define("OUTPUT_ERROR", 12, false);
define("INTERNAL_ERROR", 99, false);

# NAVRATY DEFINOVANE PRO parse.php
define("HEADER_ERROR", 21, false);
define("UNKNOWN_OPCODE", 22, false);
define("ERROR_LEX_SYNT", 23, false);

define("PRINT_ENABLE", true, false);
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
            exit(PROCCESS_OK);
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
$lines = file(FILENAME);
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
        if($i == 0) # kontrola hlavicky .IPPcode23 a jine varianty
        {
            checkHeader($lineElements);
            myPrint("HEADER OK");
        }
        else
        {
            $order++;

            switch(strtoupper($lineElements[0]))
            {
                case "ADD":
                case "SUB":
                case "MUL":
                case "IDIV":
                case "LT":
                case "GT":
                case "EQ":
                case "AND":
                case "OR":
                case "NOT":
                case "STR2INT":
                case "CONCAT":
                case "GETCHAR":
                case "SETCHAR":
                    myPrint("var symb1 symb2");
                    break;
                case "CREATEFRAME":
                case "PUSHFRAME":
                case "POPFRAME":
                case "RETURN":
                case "BREAK":
                    myPrint("*nema argumenty*");
                    break;
                case "MOVE":
                case "INT2CHAR":
                case "STRLEN":
                case "TYPE":
                    myPrint("var symb");
                    break;
                case "PUSHS":
                case "WRITE":
                case "EXIT":
                case "DPRINT":
                    myPrint("symb");
                    break;
                case "CALL":
                case "LABEL":
                case "JUMP":
                    myPrint("label");
                    break;
                case "DEFVAR":
                case "POPS":
                    myPrint("var");
                    break;
                case "JUMPIFEQ":
                case "JUMPIFNEQ":
                    myPrint("label symb1 symb2");
                    break;
                case "READ":
                    myPrint("var type");
                    break;
                default:
                    errorExit("NEROZPOZNANA INSTRUKCE!\n", UNKNOWN_OPCODE);
                    break;

            }
        }
    }
}
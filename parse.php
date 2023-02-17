<?php

# NAVRATY STEJNE PRO OBA SKRIPTY
define("PROCCESS_OK", 0, false);
define("PARAM_ERROR", 10, false);
define("INPUT_ERROR", 11, false);
define("OUTPUT_ERROR", 12, false);
define("INTERNAL_ERROR", 99, false);

# NAVRATY DEFINOVANE PRO parse.php
define("MISSING_HEADER", 21, false);
define("UNKNOWN_OPCODE", 22, false);
define("ERROR_LEX_SYNT", 23, false);

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

####################### PSEUDOMAIN #######################

$xml = new XMLWriter();
$xml->openMemory();
$xml->startDocument('1.0', 'UTF-8');
$xml->setIndent(true);
$xml->startElement('program');
$xml->writeAttribute('language', 'IPPcode23');

checkArguments($argc, $argv);
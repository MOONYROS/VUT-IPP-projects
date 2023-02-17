<?php

# NAVRATY STEJNE PRO OBA SKRIPTY
define("MISSING_PARAM", 10, false);
define("INPUT_ERROR", 11, false);
define("OUTPUT_ERROR", 12, false);
define("INTERNAL_ERROR", 99, false);

# NAVRATY DEFINOVANE PRO parse.php
define("MISSING_HEADER", 21, false);
define("UNKNOWN_OPCODE", 22, false);
define("ERROR_LEX_SYNT", 23, false);

function displayHelp()
{
    echo "TADY BUDE NEKDY NAPOVEDA\n";
}

function checkArguments($argc, $argv)
{
    if($argc > 1)
    {
        if(($argc == 2) && ($argv[1] == "--help"))
            displayHelp();
        else
            echo "MAME JINE ARGUMENTY!\n";
    }
    else
    {
        echo "ARGUMENTY NEJSOU\n";
    }
}

####################### PSEUDOMAIN #######################

echo "Tohle je start programu.\n";

$xml = new XMLWriter();
$xml->openMemory();
$xml->startDocument('1.0', 'utf-8');
$xml->setIndent(true);
$xml->startElement('program');
$xml->writeAttribute('language', 'IPPcode22');

checkArguments($argc, $argv);
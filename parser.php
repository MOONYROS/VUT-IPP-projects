<?php

define("MISSING_PARAM", 10);
define("INPUT_ERROR", 11);
define("OUTPUT_ERROR", 12);
define("INTERNAL_ERROR", 99);

function displayHelp()
{
    echo "TADY BUDE NEKDY NAPOVEDA\n";
}

function checkArguments($argc, $argv)
{
    if($argc > 1)
    {
        echo "MAME ARGUMENTY!\n";
    }
    else
    {
        echo "ARGUMENTY NEJSOU\n";
    }
}

####################### MAIN #######################

echo "Tohle je start programu.\n";

$xml = new XMLWriter();
$xml->openMemory();
$xml->startDocument('1.0', 'utf-8');
$xml->setIndent(true);
$xml->startElement('program');
$xml->writeAttribute('language', 'IPPcode22');

checkArguments($argc, $argv);
# VUT-IPP-projects (2022/2023)

Goal of these 2 projects was to make an interpret (working name **IPPCode23**) for IFJCode22 (essentialy a subset of *PHP 8*) language.
To know more about the IFJCode22 language, please see my repository with that project [here](https://github.com/MOONYROS/VUT-IFJ-project).
So, what is was basically aimed to do was to interpret *assembler-like* instructions like for any interpreted language.

## More about the tasks

First task was to parse instructions from *stdin*, do a lexical and a slight syntax analysis and then write the output into *XML file* using `PHP 8`.
For further information, please see the project documentation in `proj1/readme1.pdf`. Note that the documentation is in Czech language only.

Second task was aimed to get that *XML file* from the first one, process the information and write the results of the program onto the *stdout* while using `Python 3`.
To know more about the functionality of this projects, please see the documentation in `proj2/readme2.pdf`. Please note that the documentation is in Czech language only.

### Testing

Project 1 was tested with these following `PHP` versions:

- PHP 8.2.6
- PHP 8.1.15

Project 2 was tested with following `Python` versions:

- Python 3.11
- Python 3.10
- Python 3.9

## Project 1 detailed evaluation

- Lexical analysis (error detection): 97%
- Syntax analysis (error detection): 91%
- Instruction processing (including errors): 100%
- Complex program processing: 92%

* STATP bonus: 0%

- **Overall score** (without bonuses): 96%

## Project 2 detailed evaluation

- Lexical analysis: 100%
- Syntax analysis: 73%
- Semantic analysis: 100%
- Runtime error (detection): 100%
- Instruction interpretation: 99%
- Interpretation of complex programs: 100%
- Command line options: 70%

* FLOAT bonus: 100%
* STACK bonus: 100%
* STATI bonus: 80%

- **Overall score** (without bonuses): 98%

## Final evaluation

- Project 1 (parse.php): 7.8/8
- Project 2 (interpret.py): 15.2/12 (3.2 are bonus tasks)

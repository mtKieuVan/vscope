# VSCOPE 

A command-line tool that helps developers view different slices of code in the codebase.

## Requirement

1. Just download and run, no install more dependencies
2. As fast as posible
3. Support multiple programming language

## Dependency

1. Bash
2. Python >= 3.7


## Components:

1. Class Line: represents a line in file
  - has: file name, line number, patten for highlight part    #todo                                     
  - when printed it will be: `<file_name>:<line> <content>`   #todo                                     

2. get_match(): given pattern, search for the lines match with the pattern in current directory recursively
=> using grep command to search and get output format include file and line number #todo

3. Class Statement: represents a source code statement
  - has a list of *line*s that is part of statement structure, not statement content
  - has a prototype which is a pattern when is used in its parent stataements
  - has a list of parents which are another statements call to it
    - parent list is lazy which means the parent list is UNSET until it is get
    - parent list can also be UNSETTABLE which means the statement does not have any parent
  - has a wrapper which are a statement that conains it.
    - besides, wrapper can be UNSET mean not set yet, or be UNSETTABLE means the satement does not have wrapper
    - wrapper is lazy, mean if get wrapper, if wrapper is UNSET, the statement will as the *language* to search for its wrapper
    - get wrapper is recursively which means if a wrapper statement was get, that wrapper sattement will auto trigger get wrapper
  - refer the the *language* of it

4. Class Language: represents a programing language parser which can search and verify for source code concepts 
  - has a list of extension which detect if a file is in this langauge or not
  - get_statement() : given a line, return a *statement* that the line be in(just list lines prototype).

5. Class Result: a list of *line* in order that is the ouput result will print to user


6. get_satetment() for C language:  #todo
   - if the line end with \ loop from line to up until has #define at first then loop from line to
     down until reach the line without end with \

7. Logging: each part of code wil have a loger



## Features:

1. Users download the project source code, place it in a safe location, and then run `make init` to make the command-line tools in this project globally accessible.

   To achieve this:
   - The Makefile should include a target named init, which identifies the path to this project source code and appends a source command for the env file to ~/.bashrc.
   - The env file should set the PATH variable to include the path to this project directory.
   - An init file will be created to mark that the project has inited.

2. Users can run `make clean` then the `~/.bashrc` will be updated to remove the added about this project. The origin bashrc will be copied to backup for safe.

3. The env.sh is the config file for setting WORKDIR and some alias to quick jump to different directories they want. They can quickly open the file via `ec` make the change effect via `sc`. 

   To archive this: introduce new bash alias `ec` and `sc` in the toolbox

4. Users configure for a repository directory where contains source code of projects they are working on. Via `wp`command, they can switch to different project and

   Syntax: `wp <name>` 

   To do this:
   - Given WORKDIR variable to user set value
   - Have bash function wp() that users give  name of project, the function will create and export variable WORKSPACE that is build from WORKDIR and project name. 

5. Given a pattern, app will auto search for blocks wrap the lines that match the pattern print the output like that: #todo

   file_name.c:1  function a() {
   file_name.c:3      if (x == y) {
   file_name.c:4          line matchs pattern
   file_name.c:7      }
   file_name.c:10 }

   Noted that the line number is not continuous because some code is hiden due to this output is focusing the line that matchs the pattern and its wrapper blocks.
   The string match the pattern will be highlight.

   Syntax: `s <pattern>`

   To do this:
   - Use *get_match()* to get all lines match with the patten. Add the lines to the *result*
   - For each line, get proper *language* to *get_statement()* from the line.
   - For each *statement*, get its wrapper.
   - For all satements was get, add the statement to the *result*


6. Given a pattern, app will auto search for definition of the statement that the pattern in

   Syntax: `s def <pattern>`

   To do this:
   - Use *get_match()* to get all lines match with the pattern. Add the lines to the *result*
   - 


3. Given file_name:line app will search for file name in current directory and open the file with vim and jump to the line number.

   Syntax: `v file.c:20`

4. Given a short file name, app will search for file name match and open the file with vim. In case of there is multiple file was found, app will ask for user choose one.

   Syntax: `v part_of_file_name`


4. Given 


Use cases:

1. There is an issue, the user checks for log and detect some related log. They use (1) to get more information about the condition that make the log was show. So the user understand more about the situlation that the issue occur. Besides, via (4), they trace back to the first function of the system that is call, the first function and the most first functions will help the user identiy the external event that make the issue occur. Via the call backtree, the user know all condition require for the log was show and modify configuration nad adjust the parameters for the event to reproduce the issue. Also be clear the root cause. 



## For developer

1. Set environment varialbe to indicate log level and 


## Issues




## Notion:
- Commit prefix can be: DSG, IMP, BUG, FIX, MIS

#!/usr/bin/python

import argparse
from abc import ABC, abstractmethod
import re
import subprocess
import os
from typing import Union


class Line:
    last_opened_file_name = None
    cached_file = None

    @classmethod
    def load_file(cls, file_name:str):

        if file_name == cls.last_opened_file_name:
            return cls.cached_file

        encodings = ['utf-8', 'iso-8859-1', 'utf-16', 'utf-16-le', 'utf-16-be',
                     'utf-32', 'utf-32-le', 'utf-32-be']
    
        for encoding in encodings:
            try:
                with open(file_name, 'r', encoding=encoding) as f:
                    cls.last_opened_file_name = file_name
                    cls.cached_file = f.readlines()
                    return cls.cached_file
            except UnicodeDecodeError:
                continue
            except IOError as e:
                raise
    
        # If none of the encodings worked
        raise UnicodeDecodeError(
            'Unknown', b'', 0, 1,
            f'Failed to decode {file_name} with any of these encodings: '
            f'{encodings}'
        )

    def __init__(self, file_name:str, index:int, content:str, highlight=None):
        self.file_name = file_name
        self.index = index
        self.content = content
        self.highlight = highlight

    def clone(self):
        return Line(self.file_name, self.index, self.content, self.highlight)

    def __eq__(self, other):
        return self.file_name == other.file_name and self.index == other.index

    def __str__(self) -> str:

        RED = "[0;31m"
        RESET = "[0m"

        if self.highlight:
            content = re.sub(self.highlight, f"{RED}\\g<0>{RESET}", self.content)
        else:
            content = self.content

        return f"{self.file_name}:{self.index + 1:<5}: {content}"

    def __getattr__(self, name):
        return getattr(self.content, name)


    def __contains__(self, item):
        return item in self.content


    def match(self, pattern:str) -> bool:
        return re.search(pattern, self.content) is not None


    def move_up(self) -> bool:

        if self.index == 0:
            return False

        lines = Line.load_file(self.file_name)

        self.index -= 1
        self.highlight = None
        self.content = lines[self.index].rstrip()
        return True
        

    def move_down(self) -> bool:

        lines = Line.load_file(self.file_name)

        if self.index + 1 >= len(lines):
            return  False

        self.index += 1
        self.highlight = None
        self.content = lines[self.index].rstrip()
        return True

    def merge(self, other):
        if other.highlight:
            self.highlight = other.highlight

def get_match(pattern:str, place: str) -> list[Line]:

    grep_result = subprocess.run(["grep", "-RHn", pattern, place], capture_output=True, text=True)

    if grep_result.returncode != 0:
        return None


    res = []

    for s in grep_result.stdout.splitlines():

        file_name, line_num, content = s.split(':', 2)

        file_name = file_name.strip()
        line_num = int(line_num.strip())
        content = content.rstrip()

        res.append(Line(file_name, line_num - 1, content, highlight=pattern))

    return res


def merge_lines(lines1: list[Line], lines2: list[Line]):
    """
    Merges lines2 into lines1, keeping the list sorted and handling duplicates.

    The list is sorted by file_name and then by line index.
    If a line exists in both lists (same file and index), the highlight from lines2 is preferred.
    This function modifies lines1 in place.
    """
    if not lines2:
        return

    if not lines1:
        lines1.extend(lines2)
        return

    result = []
    i = 0
    j = 0
    while i < len(lines1) and j < len(lines2):
        line1 = lines1[i]
        line2 = lines2[j]
        
        key1 = (line1.file_name, line1.index)
        key2 = (line2.file_name, line2.index)

        if key1 < key2:
            result.append(line1)
            i += 1
        elif key2 < key1:
            result.append(line2)
            j += 1
        else:  # Keys are equal, merge
            line1.merge(line2)
            result.append(line1)
            i += 1
            j += 1

    # Add remaining lines
    if i < len(lines1):
        result.extend(lines1[i:])
    if j < len(lines2):
        result.extend(lines2[j:])

    lines1[:] = result


class Block:

    def __init__(self, lang, line: Line = None):
        self.lang = lang 
        self.lines = []
        self.start = None
        self.end = None
        if line:
            self.add(line)

    def add(self, new_line: Line):
        for existing_line in self.lines:
            if existing_line == new_line:
                existing_line.merge(new_line)
                return

        insertion_point = 0
        for i, line in enumerate(self.lines):
            if (line.file_name, line.index) < (new_line.file_name, new_line.index):
                insertion_point = i + 1
            else:
                break

        self.lines.insert(insertion_point, new_line)

    def add_start_with(self, pattern: str):
        if not self.lines:
            return

        cursor = self.lines[0].clone()

        while cursor.move_up():
            if cursor.match(pattern):
                self.add(cursor.clone())
                self.start = self.lines[0]
                return

    def fill_start_until(self, pattern: str):
        if not self.lines:
            return

        cursor = self.lines[0].clone()

        while not cursor.match(pattern):
            self.add(cursor.clone())
            cursor.move_down()

        self.add(cursor.clone())

    def add_end_with(self, pattern: str):
        if not self.lines:
            return

        cursor = self.lines[-1].clone()

        while cursor.move_down():
            if cursor.match(pattern):
                self.add(cursor.clone())
                self.end = self.lines[-1]
                return

    def fill_full(self):
        if not self.start or not self.end:
            return

        if self.start.file_name != self.end.file_name:
            return

        cursor = self.start.clone()

        while cursor.index < self.end.index - 1:
            if not cursor.move_down():
                break
            self.add(cursor.clone())

    def __str__(self):
        return "".join(str(l).rstrip() for l in self.lines)

    def __getattr__(self, name):
        return getattr(self.lines, name)


EXTENSIONS = {}

class Language (ABC):
    extensions: list[str] = []

    @abstractmethod
    def get_define_block(line:Line) -> Block : ...

    @classmethod
    def register(cls):
        instance = cls()
        name = cls.__name__.lower()
        globals()[name] = instance  # create global variables (cpp, python,...)
        for ext in getattr(cls, "extensions", []):
            EXTENSIONS[ext] = instance
        return instance

    @classmethod
    def register_all(cls):
        for subclass in cls.__subclasses__():
            subclass.register()

    @classmethod
    def get_by_filename(cls, filename: str):
        _, ext = os.path.splitext(filename)
        return EXTENSIONS.get(ext)


########## Each language in a class ##############################

class Cpp (Language):
    extensions = [".c", ".cpp", ".h", ".hpp"]


    def get_define_block(self, line: Line) -> Block:

        if not self._is_define_syntax(line):
            return None

        if line.startswith(r"#define"):
            return self.get_define_macro(line)

             

        blk = Block(Cpp, line)
        
        blk.add_start_with(r"^\s*(typedef|enum|struct|class)\b.*[^;]$")
        if not blk.start or "=" in blk.start:
            return None

        blk.fill_start_until("{")
        blk.add_end_with(r"^\s.*}.*;")

        if line == blk.start or line == blk.end or "enum" in blk.start:
            blk.fill_full()

        return blk

    def get_define_macro(self, line: Line) -> Block:

        blk = Block(Cpp, line)

        blk.add_start_with(r"#define")
        blk.fill_start_until(r"[^\\]$")

        return blk

    def get_wrapper(self, start: Line, end: Line) -> Block:
        return None

    def get_caller(self, interface: str) -> Block:
        return None

    def _is_define_syntax(self,line) -> bool:
        if line.match(r"\(.*\).*;"): 
            return False

        if line.match(r"\b(else|if|switch|do|while)\b"):
            return False

        return True
##################################################################

Language.register_all()

def search_def(pattern:str) -> list[Line]:
    lines = get_match(pattern, "../sipp")

    for l in lines:
        lang = Language.get_by_filename(l.file_name)

        if not lang:
            continue

        res = lang.get_define_block(l)
        if res:
            print(lang.get_define_block(l))
      
def search_wrapper(pattern:str) -> list[Line]:
    return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search for definitions in code.")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Subparser for the 'def' command
    def_parser = subparsers.add_parser("def", help="Search for definitions.")
    def_parser.add_argument("pattern", type=str, help="The pattern to search for.")

    args = parser.parse_args()

    if args.command == "def":
        search_def(args.pattern)
    else:
        parser.print_help()

#!/usr/bin/python

import argparse
from abc import ABC, abstractmethod
import re
import subprocess
import os
from typing import Union

def debug(fmt):
    print(f"Debug: {fmt}")
    return

QUIET = False

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

        if QUIET:
            return content
        else:
           return f"{self.file_name}:{self.index + 1:<5}: {content}"

    def get_indentation_pattern(self, suffix: str) -> str:
        match = re.match(r"^(\s*)", self.content)
        indentation = match.group(1) if match else ""
        return "^" + re.escape(indentation) + suffix

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
            self.add(line.clone())
            self.start = self.lines[0]
 

    def add(self, new_line: Line):
        """
        Adds a new Line object to the block, maintaining sorted order and handling duplicates.
        """
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

    def fill_up_until(self, pattern: str, stop_pattern: str = None) -> bool:
        if not self.lines:
            return False

        cursor = self.lines[0].clone()

        lines_to_add = []
        while cursor.move_up():
            if stop_pattern and cursor.match(stop_pattern):
                self.lines.clear()
                return False

            lines_to_add.append(cursor.clone())
            if cursor.match(pattern):
                for line in reversed(lines_to_add):
                    self.add(line)
                self.start = self.lines[0]
                return True

        return False

    def fill_down_until(self, pattern: str, stop_pattern: str = None) -> bool:
        if not self.lines:
            return False

        # Find the last continuous line from the start of the block
        current_continuous_line = self.lines[0]
        for i in range(1, len(self.lines)):
            if (self.lines[i].file_name == current_continuous_line.file_name and
                self.lines[i].index == current_continuous_line.index + 1):
                current_continuous_line = self.lines[i]
            else:
                break
        
        cursor = current_continuous_line.clone()

        # If current_continuous_line already matches the pattern, we're done
        if cursor.match(pattern):
            return True

        while cursor.move_down():
            if stop_pattern and cursor.match(stop_pattern):
                self.lines.clear()
                return False

            self.add(cursor.clone())
            if cursor.match(pattern):
                return True

        return False

    def get_start_with(self, pattern: str, stop_pattern: str = None) -> bool:
        if not self.lines:
            return False

        cursor = self.lines[0].clone()

        if cursor.match(pattern):
            self.start = self.lines[0]
            return True

        while cursor.move_up():
            if stop_pattern and cursor.match(stop_pattern):
                self.lines.clear()
                return False

            if cursor.match(pattern):
                self.add(cursor)
                self.start = self.lines[0]
                return True

        return False


    def get_end_with(self, pattern: str):
        if not self.lines:
            return

        cursor = self.lines[-1].clone()

        while cursor.move_down():
            if cursor.match(pattern):
                self.add(cursor.clone())
                self.end = self.lines[-1]
                return

    def fill_full(self):
        """
        Fills the block with all lines between `self.start` and `self.end`
        """
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
        return "\n".join(str(l) for l in self.lines)

    def __getattr__(self, name):
        return getattr(self.lines, name)


class Result:
    def __init__(self):
        self.lines = []

    def add(self, new_line: Line):
        """
        Adds a new Line object to the result, maintaining sorted order and handling duplicates.
        """
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

    def add_block(self, block: Block):
        if not block:
            return
        for line in block.lines:
            self.add(line)

    def show(self):
        for line in self.lines:
            print(line)

result = Result()


EXTENSIONS = {}

class Language (ABC):
    extensions: list[str] = []

    @abstractmethod
    def get_define(line:Line, pattern:str) -> Block : ...

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


    def get_define(self, line: Line, pattern: str) -> Block:

        # #define, with pattern in the name
        if line.match(r"^\s*#define\s+" + pattern + r"\b"):
            return self._get_define_macro(line)

        # function, with pattern in the name
        # The name part is complex, allowing for namespaces: (\w*::)*\w*PATTERN\w*
        if line.match(r"^(?!.*\)\s*;)\s*[A-Za-z_][\w\s\*\(\)]*\s+(\w*::)?" + pattern + r"\s*\("):
            return self._get_define_function(line)

        # struct/enum/union, with pattern in the name
        if line.match(r"^\s*(typedef|struct|enum|union)\s+\b\w*" + pattern + r"\w*\b"):
            return self._get_define_struct_enum_union(line)

        # typedef struct {} name; with pattern in the name
        if line.match(r"^\s*}\s*\b\w*" + pattern + r"\w*\b\s*;"):
            return self._get_define_struct_enum_union(line)

        if line.match(r"^\s*" + pattern + r"\s*(=\s*[^,}]+)?\s*,?$"):
            return self._get_define_field_enum(line)

        if line.match(r"^\s*(\w+\s+)?\w+\s+\w+\s*;$"):
            return self._get_define_field_struct_union(line)
        
        return None

    def _get_define_macro(self, line: Line) -> Block:
        blk = Block(Cpp, line)
        blk.fill_down_until(r"[^\\]$")
        return blk

    def _get_define_function(self, line: Line) -> Block:
        blk = Block(Cpp, line)
        if not ")" in blk.start and not blk.fill_down_until(r"\)", r"\);"):
            return None

        end_brace_pattern = blk.start.get_indentation_pattern(r"}.*")

        blk.fill_down_until(end_brace_pattern)
        return blk

    def _get_define_struct_enum_union(self, line: Line) -> Block:
        blk = Block(cpp, line)
        if blk.start.match(r"(struct|enum|union|typedef)"):
            blk.fill_down_until(blk.start.get_indentation_pattern(r"}.*"))
        else:
            blk.fill_up_until(blk.start.get_indentation_pattern(r"(struct|enum|union|typedef)"))

        return blk

    def _get_define_field_enum(self, line: Line) -> Block:

        blk = Block(cpp, line)

        if not blk.fill_up_until(r"\benum\b", r"(}|;)" ):
            return None

        end_brace_pattern = blk.start.get_indentation_pattern(r"}.*")
        blk.fill_down_until(end_brace_pattern)

        return blk

    def _get_define_field_struct_union(self, line: Line) -> Block:

        blk = Block(cpp, line)

        if not blk.get_start_with(r"\b(struct|union)\b.*[^;]$", r"}" ):
            return None

        end_brace_pattern = blk.start.get_indentation_pattern(r"}.*")
        blk.get_end_with(end_brace_pattern)

        return blk

    def get_wrapper(self, line: Line) -> Block:
        return self._get_function_wrapper(line)

    def _get_function_wrapper(self, line: Line) -> Block:

        blk = Block(cpp, line) 

        function_start_pattern = r"^(?!.*\)\s*;)\s*[A-Za-z_][\w\s\*\(\)]*\s+(\w*::)*\w+\s*\("
        
        if not blk.get_start_with(function_start_pattern):
            return None

        # blk.start is now the function signature line.
        # Now fill down to get the full signature until the opening brace.
        if not blk.fill_down_until(r"{", stop_pattern=r";"):
            # This is likely a function declaration, not a definition.
            return None

        # Now get the closing brace for the function
        end_brace_pattern = blk.start.get_indentation_pattern(r"}.*")
        blk.get_end_with(end_brace_pattern)
        
        return blk

    def get_caller(self, interface: str) -> Block:
        return None

##################################################################

Language.register_all()

def search_grep(pattern:str, path:str):
    lines = get_match(pattern, path)
    if lines:
        for line in lines:
            result.add(line)
        result.show()

def search_def(pattern:str):
    lines = get_match(pattern, "../sipp")

    if not lines:
        return

    for l in lines:
        lang = Language.get_by_filename(l.file_name)

        if not lang:
            continue

        res = lang.get_define(l, pattern)
        if res:
            result.add_block(res)
    result.show()
      
def search_wrapper(pattern:str):

    lines = get_match(pattern, "../sipp")

    if not lines:
        return

    for l in lines:
        lang = Language.get_by_filename(l.file_name)

        if not lang:
            continue

        res = lang.get_wrapper(l)
        if res:
            result.add_block(res)
    result.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Search for code. By default, it searches for a function wrapper. Use 'def' or 'grep' for other searches.",
        epilog="Examples:\n  s my_function_name\n  s def my_variable\n  s grep 'some text' -f /path/to/search",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress file and line number prefixes in output.")
    parser.add_argument("-f", "--path", default="../sipp", help="Path to search in for 'grep' command.")
    
    parser.add_argument("command_or_pattern", help="Command ('def', 'grep') or a pattern for a wrapper search.")
    parser.add_argument("pattern", nargs="?", help="Pattern for 'def' or 'grep' command.")

    args = parser.parse_args()

    QUIET = args.quiet

    if args.command_or_pattern == "def":
        if not args.pattern:
            parser.error("'def' command requires a pattern.")
        search_def(args.pattern)
    elif args.command_or_pattern == "grep":
        if not args.pattern:
            parser.error("'grep' command requires a pattern.")
        search_grep(args.pattern, args.path)
    else:
        if args.pattern:
            parser.error(f"Too many arguments. Did you mean 'def {args.command_or_pattern}' or 'grep {args.command_or_pattern}'?")
        search_wrapper(args.command_or_pattern)

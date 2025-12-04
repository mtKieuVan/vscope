#!/usr/bin/python

import argparse
from abc import ABC, abstractmethod
import re
import subprocess
import os
from typing import Union

def debug(fmt):
    #print(f"Debug: {fmt}")
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
        self.highlight2 = None

    def clone(self):
        cloned = Line(self.file_name, self.index, self.content, self.highlight)
        cloned.highlight2 = self.highlight2
        return cloned

    def __eq__(self, other):
        return self.file_name == other.file_name and self.index == other.index

    def __str__(self) -> str:
        content = self.get_highlighted_content()

        if QUIET:
            return content
        else:
           return f"{self.file_name}:{self.index + 1:<5}: {content}"

    def get_highlighted_content(self) -> str:
        RED = "\033[0;31m"
        BLUE = "\033[0;34m"
        RESET = "\033[0m"

        content = self.content
        if self.highlight2:
            content = re.sub(self.highlight2, f"{BLUE}\\g<0>{RESET}", content)

        if self.highlight:
            content = re.sub(self.highlight, f"{RED}\\g<0>{RESET}", content)
        
        return content


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
        if other.highlight2:
            self.highlight2 = other.highlight2

def get_match(pattern:str, place: str, extensions: list[str] = None) -> list[Line]:

    cmd = ["grep", "-ERHn", pattern, place]
    if extensions:
        for ext in extensions:
            cmd.insert(1, f"--include=*{ext}")

    grep_result = subprocess.run(cmd, capture_output=True, text=True)

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

    @abstractmethod
    def extract_function_name(self, line: Line) -> str: ...

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
    keywords = {
        "alignas", "alignof", "and", "and_eq", "asm", "atomic_cancel", "atomic_commit", 
        "atomic_noexcept", "auto", "bitand", "bitor", "bool", "break", "case", "catch",
        "char", "char8_t", "char16_t", "char32_t", "class", "compl", "concept", "const", 
        "consteval", "constexpr", "constinit", "const_cast", "continue", "co_await", 
        "co_return", "co_yield", "decltype", "default", "delete", "do", "double", 
        "dynamic_cast", "else", "enum", "explicit", "export", "extern", "false", 
        "float", "for", "friend", "goto", "if", "inline", "int", "long", "mutable", 
        "namespace", "new", "noexcept", "not", "not_eq", "nullptr", "operator", "or", 
        "or_eq", "private", "protected", "public", "reflexpr", "register", 
        "reinterpret_cast", "requires", "return", "short", "signed", "sizeof", "static", 
        "static_assert", "static_cast", "struct", "switch", "synchronized", "template", 
        "this", "thread_local", "throw", "true", "try", "typedef", "typeid", "typename", 
        "union", "unsigned", "using", "virtual", "void", "volatile", "wchar_t", "while",
        "xor", "xor_eq"
    }


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

    def extract_function_name(self, line: Line) -> str:
        content = line.content
        last_paren_index = content.rfind('(')
        if last_paren_index == -1:
            return None
        
        before_paren = content[:last_paren_index]
        
        match = re.search(r"(\b\w+(?:::\w+)*)\s*$", before_paren.strip())
        if match:
            return match.group(1).split("::")[-1]

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

    def get_function_wrapper(self, line: Line) -> Block:

        #function_start_pattern = r"^(?!.*\)\s*;)\s*[A-Za-z_][\w\s\*\(\)]*\s+(\w*::)*\w+\s*\("
        function_start_pattern = r"^(?!.*\)\s*;)(?!\s*(?:if|else|for|while|switch|catch|return)\b)(?:\s*[A-Za-z_][\w\s\*\(\):<>]*\s+(?:\w+::)*\w+\s*\(|(?:\w+::)*\w+\s*\()"
        
        # If the line itself is a function definition, it can't have a wrapper in this context.
        if line.match(function_start_pattern):
            return None

        blk = Block(cpp, line) 

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

    lines = get_match(pattern, "./")

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

    lines = get_match(pattern, "./")

    if not lines:
        return

    for l in lines:
        lang = Language.get_by_filename(l.file_name)

        if not lang:
            continue

        res = lang.get_function_wrapper(l)
        if res:
            result.add_block(res)
    result.show()

def get_caller_blocks(pattern: str, search_path: str, extensions: list[str] = None) -> list[tuple[Block, Line]]:
    debug(f"get_caller_blocks: Searching for pattern '{pattern}' in '{search_path}' with extensions: {extensions}")
    lines = get_match(pattern, search_path, extensions)
    if not lines:
        debug(f"get_caller_blocks: No matches found for '{pattern}'")
        return []

    caller_info_list = []
    seen_block_ids = set() # To store IDs of wrapper blocks already added

    for line in lines: # `line` here is the Line object where `pattern` was found
        lang = Language.get_by_filename(line.file_name)
        if not lang:
            debug(f"get_caller_blocks: No language found for file '{line.file_name}'")
            continue

        wrapper_block = lang.get_function_wrapper(line)
        if not wrapper_block or not wrapper_block.start:
            debug(f"get_caller_blocks: No wrapper block found for line '{line.content.strip()}' (where pattern was found)")
            continue
            
        block_id = f"{wrapper_block.start.file_name}:{wrapper_block.start.index}"
        if block_id not in seen_block_ids:
            caller_info_list.append((wrapper_block, line)) # Store both the wrapper block and the call line
            seen_block_ids.add(block_id)
            debug(f"get_caller_blocks: Found caller block '{block_id}' for '{pattern}' (content: {wrapper_block.start.content.strip()}), called from {line.file_name}:{line.index + 1}")
            
    debug(f"get_caller_blocks: Returning {len(caller_info_list)} caller blocks for '{pattern}'")
    return caller_info_list

def print_top_down_tree(caller_id: str, callees_of: dict, nodes: dict, visited_ids: set, prefix: str):
    if caller_id in visited_ids:
        return
    visited_ids.add(caller_id)

    if caller_id not in callees_of:
        return

    callees = callees_of.get(caller_id, [])
    for i, callee_info in enumerate(callees):
        is_last = (i == len(callees) - 1)
        connector = "└── " if is_last else "├── "
        
        callee_name = callee_info['name']
        call_line = callee_info['line']
        
        callee_id = None
        for n_id, n_info in nodes.items():
            if n_info['name'] == callee_name:
                callee_id = n_id
                break

        if callee_id and callee_id in nodes:
            print(f"{prefix}{connector}{nodes[callee_id]['line'].get_highlighted_content().strip()} ({nodes[callee_id]['line'].file_name}:{nodes[callee_id]['line'].index+1})")

            new_prefix = prefix + ("    " if is_last else "│   ")
            child_connector = "    "
            print(f"{new_prefix}{child_connector}{call_line.get_highlighted_content().strip()} ({call_line.file_name}:{call_line.index+1})")
        else:
            print(f"{prefix}{connector}{call_line.get_highlighted_content().strip()} ({call_line.file_name}:{call_line.index+1})")

        
        if callee_id:
            new_prefix = prefix + ("    " if is_last else "│   ")
            print_top_down_tree(callee_id, callees_of, nodes, visited_ids, new_prefix)


def search_tree(pattern: str, max_level: int = 10):
    debug(f"search_tree: Starting for pattern '{pattern}' with max level {max_level}")
    search_path = "./"

    nodes = {}
    callers_of = {}

    queue = [(pattern, 0, None)] # (pattern, level, extensions)
    processed_patterns = {pattern}

    while queue:
        current_pattern, level, current_extensions = queue.pop(0)

        if level >= max_level:
            continue

        search_p = current_pattern if level == 0 else r"\b" + re.escape(current_pattern) + r"\b.*\("
        
        caller_info_list = get_caller_blocks(search_p, search_path, extensions=current_extensions)
        
        if not caller_info_list:
            continue

        if current_pattern not in callers_of:
            callers_of[current_pattern] = []

        for wrapper_block, call_line in caller_info_list:
            if level > 0:
                call_line.highlight = None

            caller_name = wrapper_block.lang.extract_function_name(wrapper_block.start)
            if not caller_name or caller_name in wrapper_block.lang.keywords:
                continue
            
            wrapper_block.start.highlight2 = r"\b" + caller_name + r"\b"
            caller_id = f"{wrapper_block.start.file_name}:{wrapper_block.start.index}"
            debug(f"caller_id = {caller_id}")

            if caller_id not in nodes:
                nodes[caller_id] = {'name': caller_name, 'lang': wrapper_block.lang, 'line': wrapper_block.start}
            
            callers_of[current_pattern].append((caller_id, call_line))

            if caller_name not in processed_patterns:
                processed_patterns.add(caller_name)
                queue.append((caller_name, level + 1, wrapper_block.lang.extensions))

    # --- Invert graph for printing ---
    callees_of = {node_id: [] for node_id in nodes}
    all_callee_names = set(callers_of.keys())

    for callee_name, caller_list in callers_of.items():
        for caller_id, call_line in caller_list:
            if caller_id in callees_of:
                callees_of[caller_id].append({'name': callee_name, 'line': call_line})

    # --- Find roots ---
    all_caller_ids = set(nodes.keys())
    callee_ids_of_callers = set()
    for name in all_callee_names:
        for node_id, node_info in nodes.items():
            if node_info['name'] == name:
                # This node is a callee of another node in the graph
                if name != pattern: # The original pattern can also be a root
                    callee_ids_of_callers.add(node_id)
    
    root_ids = all_caller_ids - callee_ids_of_callers

    # --- Print from roots ---
    print(f"Call tree for '{pattern}':")
    if not root_ids and not callees_of:
         print(f"No callers found for '{pattern}'.")
         return

    if not root_ids and nodes:
        root_ids = list(nodes.keys())


    for root_id in root_ids:
        line = nodes[root_id]['line']
        print(f"{line.get_highlighted_content().strip()} ({line.file_name}:{line.index+1})")
        print_top_down_tree(root_id, callees_of, nodes, set(), "")
        print("-" * 20)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Search for code. By default, it searches for a function wrapper. Use 'def' or 'grep' for other searches.",
        epilog="Examples:\n  s my_function_name\n  s def my_variable\n  s grep 'some text' -f /path/to/search\n  s tree my_function -l 5",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress file and line number prefixes in output.")
    parser.add_argument("-f", "--path", default="./", help="Path to search in for 'grep' command.")
    parser.add_argument("-l", "--level", type=int, default=5, help="Maximum recursion depth for 'tree' command.")
    
    parser.add_argument("command_or_pattern", help="Command ('def', 'grep', 'tree') or a pattern for a wrapper search.")
    parser.add_argument("pattern", nargs="?", help="Pattern for 'def', 'grep', or 'tree' command.")

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
    elif args.command_or_pattern == "tree":
        if not args.pattern:
            parser.error("'tree' command requires a pattern.")
        search_tree(args.pattern, args.level)
    else:
        if args.pattern:
            parser.error(f"Too many arguments. Did you mean 'def {args.command_or_pattern}' or 'grep {args.command_or_pattern}'?")
        search_wrapper(args.command_or_pattern)

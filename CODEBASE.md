# Vscope

## Search tree

Ví dụ:
```
int main(int argc, char* argv[]) (../sipp/src/sipp_unittest.cpp:26)
└── scenario::scenario(char * filename, int deflt) (../sipp/src/scenario.cpp:696)
       main_scenario = new scenario(0, 0); (../sipp/src/sipp_unittest.cpp:30)
   └── void scenario::getCommonAttributes(message *message) (../sipp/src/scenario.cpp:1854)
           getCommonAttributes(nopmsg); (../sipp/src/scenario.cpp:821)
       └── bool call::lost(int index) (../sipp/src/call.cpp:1417)
               message -> lost = get_double(ptr, "lost percentage"); (../sipp/src/scenario.cpp:1862)
           └── srand((unsigned int) time(nullptr)); (../sipp/src/call.cpp:1433)
```

Debug log:
```
Searching for pattern 'getSessionStateCurrent' in '../sipp' with extensions: None                                             # đang work trên một pattern
Found caller block '../sipp/src/call.cpp:2574' for 'getSessionStateCurrent' (content: char* call::createSendingMessage(...       # dòng grep thứ nhất tìm được wrapper
Found caller block '../sipp/src/call.cpp:4509' for 'getSessionStateCurrent' (content: bool call::process_incoming(...            # dòng grep thứ hai tìm được wrapper
No wrapper block found for line 'SessionState call::getSessionStateCurrent()' (where pattern was found)                          # dòng grep này không được wrap
Returning 2 caller blocks for 'getSessionStateCurrent'                                                                           # tổng kết được 2 caller
```

Code flow:
```
search_tree(pattern)
	nodes = {}                                                       # dict các caller phân biệt bằng file_name và start_line index
	callers_of = {}                                                  # tree chứa kết quả pattern và các wrapper gọi nó
	queue = [(pattern, 0)] # (pattern, level)                        # queue chứa các pattern cần tìm wrapper
	while queue:
		current_pattern, level = queue.pop(0)
		search_p = current_pattern
		caller_info_list = get_caller_blocks(search_p)               # lấy ra tất cả các line khớp pattern và function tương ứng wrap line đó
			lines = get_match(pattern)
			for line in lines:
				wrapper_block = lang.get_function_wrapper(line)
				caller_info_list.append((wrapper_block, line))
			return caller_info_list
		for wrapper_block, call_line in caller_info_list:            # với mối wrapper function:
			caller_name = extract_function_name(wrapper_block.start)    # lấy ra function name
		    nodes[caller_id] = caller_name                              # add name vào danh sách caller kèm với caller id (file:line)
			callers_of[current_pattern].append((caller_id, call_line))  # add vào tree kết quả caller id cùng với vị trí pattern được gọi trong caller đó
			queue.append((caller_name, level + 1))                      # add queue để tiếp tục tìm wrapper cho caller
		
		callees_of[] = ...                                           # đảo ngược tree để đi từ caller xuống callee cho việc hiển thị
		root_ids[] = ...                                             # tìm danh sách các root
		for root_id in root_ids:                                     # với mỗi root, in ra màng hình các nhánh con của nó
			print_top_down_tree(root_id, callees_of, nodes)         
```
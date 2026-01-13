import os
import re

def get_imports(file_path):
    imports = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Match import ... from '...'
            matches = re.findall(r"from\s+['\"]([^'\"]+)['\"]", content)
            imports.extend(matches)
            # Match import '...'
            matches_direct = re.findall(r"import\s+['\"]([^'\"]+)['\"]", content)
            imports.extend(matches_direct)
    except Exception as e:
        pass
    return imports

def find_cycles(start_dir):
    graph = {}
    file_map = {} # path -> canonical path

    # 1. Build map of all files
    for root, dirs, files in os.walk(start_dir):
        for file in files:
            if file.endswith('.ts') or file.endswith('.tsx'):
                full_path = os.path.join(root, file)
                # Store relative to start_dir for easier reading, but use full for unique ID
                rel_path = os.path.relpath(full_path, start_dir)
                # Remove extension for import matching
                key = os.path.splitext(rel_path)[0]
                if key.endswith('/index'):
                    key = os.path.dirname(key)
                
                graph[key] = []
                file_map[key] = full_path

    # 2. Build Graph
    for key, full_path in file_map.items():
        raw_imports = get_imports(full_path)
        for imp in raw_imports:
            if imp.startswith('.'):
                # Resolve relative import
                # dir of current file
                current_dir = os.path.dirname(key)
                resolved = os.path.normpath(os.path.join(current_dir, imp))
                
                # Check if this resolves to a known file
                if resolved in graph:
                    graph[key].append(resolved)
                else:
                    # Try adding /index
                    resolved_index = os.path.join(resolved, 'index')
                    if resolved_index in graph: # unlikely with my key logic but possible
                        graph[key].append(resolved_index)

    # 3. DFS for cycles
    visited = set()
    rec_stack = set()
    cycles = []

    def dfs(u, path):
        visited.add(u)
        rec_stack.add(u)
        path.append(u)

        if u in graph:
            for v in graph[u]:
                if v not in visited:
                    dfs(v, path)
                elif v in rec_stack:
                    # Cycle found
                    cycle_slice = path[path.index(v):]
                    cycles.append(cycle_slice)

        rec_stack.remove(u)
        path.pop()

    for node in graph:
        if node not in visited:
            dfs(node, [])

    if cycles:
        print(f"Found {len(cycles)} circular dependencies:")
        for c in cycles:
            print(" -> ".join(c))
            print("---")
    else:
        print("No circular dependencies found.")

if __name__ == "__main__":
    find_cycles("frontend/src")

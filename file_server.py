#!/usr/bin/env python3
"""
A simple HTTP file server with directory listing, file search, and markdown rendering.
Similar to Apache mod_autoindex but with enhanced features.
"""

import http.server
import socketserver
import os
import re
import subprocess
import urllib.parse
import html
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import shutil
import mimetypes

PORT = 8000
HOST = '127.0.0.1'
ROOT_DIR = os.getcwd()
DEFAULT_PAGE_SIZE = 20
PAGE_SIZES = [20, 50, 100, 'all']

TEXT_EXTENSIONS = {
    '.txt', '.md', '.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.hpp',
    '.json', '.xml', '.yaml', '.yml', '.html', '.css', '.sh', '.bash',
    '.conf', '.cfg', '.ini', '.log', '.rst', '.tex', '.sql', '.php',
    '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.lua', '.pl',
    '.r', '.m', '.h', '.hpp', '.cs', '.vb', '.asm', '.s', '.vue',
    '.jsx', '.tsx', '.svelte', '.dockerfile', '.makefile', '.cmake',
    '.toml', '.env', '.gitignore', '.dockerignore', '.editorconfig'
}

CODE_EXTENSIONS = {
    '.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.hpp', '.cs',
    '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.lua', '.pl',
    '.php', '.r', '.m', '.asm', '.s', '.vue', '.jsx', '.tsx', '.svelte',
    '.sql', '.sh', '.bash', '.json', '.xml', '.yaml', '.yml', '.html',
    '.css', '.toml', '.ini', '.conf', '.cfg', '.env'
}


class SearchResult:
    def __init__(self, file_path: str, line_number: int, line_content: str, match_start: int, match_end: int):
        self.file_path = file_path
        self.line_number = line_number
        self.line_content = line_content
        self.match_start = match_start
        self.match_end = match_end


class FileServerHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.root_dir = ROOT_DIR
        super().__init__(*args, directory=ROOT_DIR, **kwargs)
    
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)
        
        if 'search' in query_params:
            self.handle_search(query_params, parsed_path.path)
        elif 'content_search' in query_params:
            self.handle_content_search(query_params, parsed_path.path)
        else:
            path = urllib.parse.unquote(parsed_path.path)
            full_path = os.path.normpath(os.path.join(self.root_dir, path.lstrip('/')))
            
            if not full_path.startswith(self.root_dir):
                self.send_error(403, "Forbidden")
                return
            
            if os.path.isdir(full_path):
                index_files = ['index.html', 'index.htm', 'index.md']
                has_index = any(os.path.exists(os.path.join(full_path, f)) for f in index_files)
                
                if has_index and not path.endswith('/'):
                    self.send_response(302)
                    self.send_header('Location', path + '/')
                    self.end_headers()
                    return
                
                sort_by = query_params.get('sort', ['name'])[0]
                sort_order = query_params.get('order', ['asc'])[0]
                self.serve_directory_listing(full_path, path, sort_by, sort_order)
            elif os.path.isfile(full_path):
                ext = os.path.splitext(full_path)[1].lower()
                if full_path.endswith('.md'):
                    self.serve_markdown(full_path)
                elif ext in CODE_EXTENSIONS:
                    self.serve_code_file(full_path)
                else:
                    super().do_GET()
            else:
                self.send_error(404, "File not found")
    
    def serve_code_file(self, file_path: str):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            rel_path = os.path.relpath(file_path, self.root_dir)
            ext = os.path.splitext(file_path)[1].lower()
            
            html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(rel_path)}</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">
<style>
{self.get_css_styles()}
.code-container {{
    max-width: 100%;
    margin: 0;
    padding: 20px;
    background: #f6f8fa;
}}
.code-header {{
    background: #fff;
    padding: 10px 15px;
    border: 1px solid #e1e4e8;
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.code-header h2 {{
    margin: 0;
    font-size: 16px;
    color: #24292e;
}}
.code-header .file-info {{
    color: #586069;
    font-size: 14px;
}}
pre {{
    margin: 0;
    padding: 16px;
    background: #fff;
    border: 1px solid #e1e4e8;
    border-radius: 0 0 6px 6px;
    overflow-x: auto;
}}
code {{
    font-family: 'SF Mono', 'Monaco', 'Menlo', 'Consolas', monospace;
    font-size: 13px;
    line-height: 1.6;
}}
.hljs {{
    background: transparent;
    padding: 0;
}}
.line-numbers {{
    counter-reset: line;
}}
.line-numbers .line {{
    counter-increment: line;
}}
.line-numbers .line::before {{
    content: counter(line);
    display: inline-block;
    width: 3em;
    margin-right: 1em;
    text-align: right;
    color: #bbb;
    border-right: 1px solid #e1e4e8;
    padding-right: 1em;
    user-select: none;
}}
</style>
</head>
<body>
<div class="container">
<p><a href="javascript:history.back()">← 返回</a></p>
<div class="code-container">
<div class="code-header">
<h2>{html.escape(os.path.basename(file_path))}</h2>
<span class="file-info">{html.escape(rel_path)}</span>
</div>
<pre><code class="language-{self.get_language_class(ext)} line-numbers">{html.escape(content)}</code></pre>
</div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<script>
document.addEventListener('DOMContentLoaded', function() {{
    hljs.highlightAll();
    
    var codeBlock = document.querySelector('code');
    var lines = codeBlock.innerHTML.split('\\n');
    var numberedLines = lines.map(function(line, index) {{
        return '<span class="line">' + line + '</span>';
    }});
    codeBlock.innerHTML = numberedLines.join('\\n');
}});
</script>
</body>
</html>'''
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', len(html_content.encode('utf-8')))
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
        except IOError:
            self.send_error(404, "File not found")
    
    def get_language_class(self, ext: str) -> str:
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.rb': 'ruby',
            '.go': 'go',
            '.rs': 'rust',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.lua': 'lua',
            '.pl': 'perl',
            '.php': 'php',
            '.r': 'r',
            '.m': 'objectivec',
            '.asm': 'x86asm',
            '.s': 'x86asm',
            '.vue': 'vue',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.svelte': 'javascript',
            '.sql': 'sql',
            '.sh': 'bash',
            '.bash': 'bash',
            '.json': 'json',
            '.xml': 'xml',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.html': 'html',
            '.css': 'css',
            '.toml': 'ini',
            '.ini': 'ini',
            '.conf': 'ini',
            '.cfg': 'ini',
            '.env': 'bash'
        }
        return lang_map.get(ext, 'plaintext')
    
    def serve_directory_listing(self, dir_path: str, web_path: str, sort_by: str = 'name', sort_order: str = 'asc'):
        try:
            entries = self.list_directory(dir_path, sort_by, sort_order)
            html_content = self.generate_directory_html(dir_path, web_path, entries, sort_by, sort_order)
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', len(html_content.encode('utf-8')))
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
        except PermissionError:
            self.send_error(403, "Permission denied")
    
    def list_directory(self, dir_path: str, sort_by: str = 'name', sort_order: str = 'asc') -> List[Tuple[str, str, int, float]]:
        entries = []
        try:
            for name in os.listdir(dir_path):
                full_path = os.path.join(dir_path, name)
                if os.path.isdir(full_path):
                    mtime = os.path.getmtime(full_path)
                    entries.append((name, 'directory', 0, mtime))
                else:
                    size = os.path.getsize(full_path)
                    mtime = os.path.getmtime(full_path)
                    entries.append((name, 'file', size, mtime))
            
            def sort_key(entry):
                name, entry_type, size, mtime = entry
                if sort_by == 'name':
                    return (entry_type != 'directory', name.lower())
                elif sort_by == 'size':
                    return (entry_type != 'directory', size if entry_type == 'file' else 0)
                elif sort_by == 'modified':
                    return (entry_type != 'directory', mtime)
                else:
                    return (entry_type != 'directory', name.lower())
            
            entries.sort(key=sort_key, reverse=(sort_order == 'desc'))
        except PermissionError:
            pass
        return entries
    
    def generate_directory_html(self, dir_path: str, web_path: str, entries: List[Tuple[str, str, int, float]], sort_by: str = 'name', sort_order: str = 'asc') -> str:
        parent_path = os.path.dirname(web_path.rstrip('/'))
        if parent_path != '/':
            parent_path = parent_path + '/'
        
        def get_sort_url(column: str) -> str:
            if sort_by == column:
                new_order = 'desc' if sort_order == 'asc' else 'asc'
            else:
                new_order = 'asc'
            return f"{web_path}?sort={column}&order={new_order}"
        
        def get_sort_indicator(column: str) -> str:
            if sort_by == column:
                return ' ↓' if sort_order == 'asc' else ' ↑'
            return ''
        
        html_parts = [
            '<!DOCTYPE html>',
            '<html lang="zh-CN">',
            '<head>',
            '<meta charset="UTF-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f'<title>Index of {html.escape(web_path)}</title>',
            '<style>',
            self.get_css_styles(),
            '</style>',
            '</head>',
            '<body>',
            '<div class="container">',
            f'<h1>Index of {html.escape(web_path)}</h1>',
            '<div class="search-box">',
            '<form method="GET" class="search-form">',
            '<div class="search-row">',
            '<input type="text" name="search" placeholder="文件名搜索（支持正则）" class="search-input">',
            '<button type="submit" class="btn">搜索文件名</button>',
            '</div>',
            '</form>',
            '<form method="GET" class="search-form">',
            '<div class="search-row">',
            '<input type="text" name="content_search" placeholder="文件内容搜索（支持正则）" class="search-input">',
            '<button type="submit" class="btn btn-secondary">搜索内容</button>',
            '</div>',
            '</form>',
            '</div>',
            '<hr>',
            '<table class="file-list">',
            '<thead>',
            '<tr>',
            f'<th><a href="{get_sort_url("name")}">Name{get_sort_indicator("name")}</a></th>',
            f'<th><a href="{get_sort_url("size")}">Size{get_sort_indicator("size")}</a></th>',
            f'<th><a href="{get_sort_url("modified")}">Modified{get_sort_indicator("modified")}</a></th>',
            '</tr>',
            '</thead>',
            '<tbody>',
        ]
        
        if web_path != '/':
            html_parts.append(f'<tr><td><a href="{html.escape(parent_path)}">../</a></td><td>-</td><td>-</td></tr>')
        
        for name, entry_type, size, mtime in entries:
            link_path = os.path.join(web_path, name)
            if entry_type == 'directory':
                link_path += '/'
                display_name = name + '/'
                size_str = '-'
            else:
                display_name = name
                size_str = self.format_size(size)
            
            mtime_str = self.format_time(mtime)
            
            html_parts.append(
                f'<tr><td><a href="{html.escape(link_path)}">{html.escape(display_name)}</a></td>'
                f'<td>{size_str}</td><td>{mtime_str}</td></tr>'
            )
        
        html_parts.extend([
            '</tbody>',
            '</table>',
            '<hr>',
            '<div class="footer">',
            f'<p>Python HTTP File Server - Port {PORT}</p>',
            '</div>',
            '</div>',
            '</body>',
            '</html>'
        ])
        
        return '\n'.join(html_parts)
    
    def handle_search(self, query_params: Dict, base_path: str):
        search_term = query_params.get('search', [''])[0]
        if not search_term:
            self.serve_directory_listing(
                os.path.join(self.root_dir, base_path.lstrip('/')),
                base_path
            )
            return
        
        try:
            pattern = re.compile(search_term)
        except re.error:
            pattern = re.compile(re.escape(search_term))
        
        results = self.search_filenames(base_path, pattern)
        page = int(query_params.get('page', ['1'])[0])
        page_size = query_params.get('page_size', [str(DEFAULT_PAGE_SIZE)])[0]
        
        if page_size == 'all':
            page_size = len(results)
        else:
            page_size = int(page_size)
        
        html_content = self.generate_search_results_html(
            search_term, results, page, page_size, 'filename', base_path
        )
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(html_content.encode('utf-8')))
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def handle_content_search(self, query_params: Dict, base_path: str):
        search_term = query_params.get('content_search', [''])[0]
        if not search_term:
            self.serve_directory_listing(
                os.path.join(self.root_dir, base_path.lstrip('/')),
                base_path
            )
            return
        
        try:
            pattern = re.compile(search_term)
        except re.error:
            pattern = re.compile(re.escape(search_term))
        
        results = self.search_file_contents(base_path, pattern)
        page = int(query_params.get('page', ['1'])[0])
        page_size = query_params.get('page_size', [str(DEFAULT_PAGE_SIZE)])[0]
        
        if page_size == 'all':
            page_size = len(results)
        else:
            page_size = int(page_size)
        
        html_content = self.generate_search_results_html(
            search_term, results, page, page_size, 'content', base_path
        )
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(html_content.encode('utf-8')))
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def search_filenames(self, base_path: str, pattern: re.Pattern) -> List[str]:
        results = []
        search_dir = os.path.join(self.root_dir, base_path.lstrip('/'))
        
        for root, dirs, files in os.walk(search_dir):
            for name in files + dirs:
                if pattern.search(name):
                    rel_path = os.path.relpath(os.path.join(root, name), self.root_dir)
                    results.append(rel_path)
        
        return sorted(results)
    
    def search_file_contents(self, base_path: str, pattern: re.Pattern) -> List[SearchResult]:
        results = []
        search_dir = os.path.join(self.root_dir, base_path.lstrip('/'))
        
        if shutil.which('rg'):
            results = self.search_with_ripgrep(search_dir, pattern)
        elif shutil.which('grep'):
            results = self.search_with_grep(search_dir, pattern)
        else:
            results = self.search_with_python(search_dir, pattern)
        
        return results
    
    def search_with_ripgrep(self, search_dir: str, pattern: re.Pattern) -> List[SearchResult]:
        results = []
        try:
            cmd = ['rg', '-n', '--no-heading', '--with-filename', pattern.pattern, search_dir]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            for line in proc.stdout.split('\n'):
                if not line:
                    continue
                
                match = re.match(r'^(.+?):(\d+):(.*)$', line)
                if match:
                    file_path, line_num, content = match.groups()
                    rel_path = os.path.relpath(file_path, self.root_dir)
                    
                    results.append(SearchResult(
                        file_path=rel_path,
                        line_number=int(line_num),
                        line_content=content,
                        match_start=0,
                        match_end=len(content)
                    ))
        except (subprocess.TimeoutExpired, Exception):
            pass
        
        return results
    
    def search_with_grep(self, search_dir: str, pattern: re.Pattern) -> List[SearchResult]:
        results = []
        try:
            cmd = ['grep', '-r', '-n', '-E', pattern.pattern, search_dir]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            for line in proc.stdout.split('\n'):
                if not line:
                    continue
                
                match = re.match(r'^(.+?):(\d+):(.*)$', line)
                if match:
                    file_path, line_num, content = match.groups()
                    rel_path = os.path.relpath(file_path, self.root_dir)
                    
                    results.append(SearchResult(
                        file_path=rel_path,
                        line_number=int(line_num),
                        line_content=content,
                        match_start=0,
                        match_end=len(content)
                    ))
        except (subprocess.TimeoutExpired, Exception):
            pass
        
        return results
    
    def search_with_python(self, search_dir: str, pattern: re.Pattern) -> List[SearchResult]:
        results = []
        
        for root, dirs, files in os.walk(search_dir):
            for name in files:
                file_path = os.path.join(root, name)
                ext = os.path.splitext(name)[1].lower()
                
                if ext not in TEXT_EXTENSIONS and not self.is_text_file(file_path):
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            if pattern.search(line):
                                rel_path = os.path.relpath(file_path, self.root_dir)
                                match = pattern.search(line)
                                
                                results.append(SearchResult(
                                    file_path=rel_path,
                                    line_number=line_num,
                                    line_content=line.rstrip('\n\r'),
                                    match_start=match.start() if match else 0,
                                    match_end=match.end() if match else len(line)
                                ))
                except (IOError, OSError):
                    continue
        
        return results
    
    def is_text_file(self, file_path: str) -> bool:
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(8192)
                if b'\x00' in chunk:
                    return False
            return True
        except:
            return False
    
    def generate_search_results_html(self, search_term: str, results: List, page: int,
                                     page_size: int, search_type: str, base_path: str) -> str:
        total_results = len(results)
        total_pages = (total_results + page_size - 1) // page_size if page_size > 0 else 1
        page = max(1, min(page, total_pages))
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_results = results[start_idx:end_idx]
        
        search_param = 'search' if search_type == 'filename' else 'content_search'
        
        html_parts = [
            '<!DOCTYPE html>',
            '<html lang="zh-CN">',
            '<head>',
            '<meta charset="UTF-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
            f'<title>Search Results for "{html.escape(search_term)}"</title>',
            '<style>',
            self.get_css_styles(),
            '</style>',
            '</head>',
            '<body>',
            '<div class="container">',
            f'<h1>搜索结果: {html.escape(search_term)}</h1>',
            f'<p>找到 {total_results} 个结果 (第 {page}/{total_pages} 页)</p>',
            '<div class="page-size-selector">',
            '每页显示: ',
        ]
        
        for size in PAGE_SIZES:
            if size == page_size or (size == 'all' and page_size == total_results):
                html_parts.append(f'<span class="current-page">{size}</span> ')
            else:
                size_str = str(size)
                html_parts.append(
                    f'<a href="?{search_param}={urllib.parse.quote(search_term)}&page=1&page_size={size_str}">{size}</a> '
                )
        
        html_parts.append('</div>')
        
        if search_type == 'filename':
            html_parts.append('<ul class="search-results">')
            for result in page_results:
                link_path = '/' + result.replace(os.sep, '/')
                html_parts.append(
                    f'<li><a href="{html.escape(link_path)}">{html.escape(result)}</a></li>'
                )
            html_parts.append('</ul>')
        else:
            html_parts.append('<div class="content-search-results">')
            for result in page_results:
                link_path = '/' + result.file_path.replace(os.sep, '/')
                html_parts.append('<div class="result-item">')
                html_parts.append(
                    f'<div class="result-file"><a href="{html.escape(link_path)}">{html.escape(result.file_path)}</a></div>'
                )
                html_parts.append(
                    f'<div class="result-line">Line {result.line_number}: {html.escape(result.line_content)}</div>'
                )
                html_parts.append('</div>')
            html_parts.append('</div>')
        
        if total_pages > 1:
            html_parts.append('<div class="pagination">')
            
            if page > 1:
                html_parts.append(
                    f'<a href="?{search_param}={urllib.parse.quote(search_term)}&page={page-1}&page_size={page_size}">上一页</a> '
                )
            
            for p in range(max(1, page - 2), min(total_pages + 1, page + 3)):
                if p == page:
                    html_parts.append(f'<span class="current-page">{p}</span> ')
                else:
                    html_parts.append(
                        f'<a href="?{search_param}={urllib.parse.quote(search_term)}&page={p}&page_size={page_size}">{p}</a> '
                    )
            
            if page < total_pages:
                html_parts.append(
                    f'<a href="?{search_param}={urllib.parse.quote(search_term)}&page={page+1}&page_size={page_size}">下一页</a>'
                )
            
            html_parts.append('</div>')
        
        html_parts.extend([
            '<hr>',
            f'<p><a href="{html.escape(base_path)}">返回目录</a></p>',
            '</div>',
            '</body>',
            '</html>'
        ])
        
        return '\n'.join(html_parts)
    
    def serve_markdown(self, file_path: str):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            rel_path = os.path.relpath(file_path, self.root_dir)
            
            html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(rel_path)}</title>
</head>
<body>
<p><a href="javascript:history.back()">← 返回</a></p>
{content}
<!-- Markdeep: --><style class="fallback">body{{visibility:hidden;white-space:pre;font-family:monospace}}</style><script src="markdeep.min.js" charset="utf-8"></script><script src="https://morgan3d.github.io/markdeep/latest/markdeep.min.js" charset="utf-8"></script><script>window.alreadyProcessedMarkdeep||(document.body.style.visibility="visible")</script>
</body>
</html>'''
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', len(html_content.encode('utf-8')))
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
        except IOError:
            self.send_error(404, "File not found")
    
    def get_css_styles(self) -> str:
        return '''
* {
    box-sizing: border-box;
}
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    line-height: 1.6;
    color: #333;
    background: #f5f5f5;
    margin: 0;
    padding: 0;
}
.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
    background: white;
    min-height: 100vh;
}
h1 {
    color: #2c3e50;
    border-bottom: 2px solid #3498db;
    padding-bottom: 10px;
}
.search-box {
    margin: 20px 0;
    padding: 15px;
    background: #f8f9fa;
    border-radius: 5px;
}
.search-form {
    margin-bottom: 10px;
}
.search-row {
    display: flex;
    gap: 10px;
}
.search-input {
    flex: 1;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 14px;
}
.btn {
    padding: 10px 20px;
    background: #3498db;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
}
.btn:hover {
    background: #2980b9;
}
.btn-secondary {
    background: #27ae60;
}
.btn-secondary:hover {
    background: #229954;
}
.file-list {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
}
.file-list th, .file-list td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}
.file-list th {
    background: #f8f9fa;
    font-weight: 600;
}
.file-list th a {
    color: #2c3e50;
    text-decoration: none;
    display: block;
}
.file-list th a:hover {
    color: #3498db;
}
.file-list tr:hover {
    background: #f8f9fa;
}
.file-list a {
    color: #3498db;
    text-decoration: none;
}
.file-list a:hover {
    text-decoration: underline;
}
.search-results {
    list-style: none;
    padding: 0;
}
.search-results li {
    padding: 10px;
    border-bottom: 1px solid #eee;
}
.search-results a {
    color: #3498db;
    text-decoration: none;
}
.search-results a:hover {
    text-decoration: underline;
}
.content-search-results {
    margin: 20px 0;
}
.result-item {
    padding: 15px;
    border: 1px solid #ddd;
    margin-bottom: 10px;
    border-radius: 4px;
    background: #fafafa;
}
.result-file {
    font-weight: 600;
    margin-bottom: 5px;
}
.result-file a {
    color: #3498db;
    text-decoration: none;
}
.result-file a:hover {
    text-decoration: underline;
}
.result-line {
    color: #666;
    font-family: 'Courier New', monospace;
    font-size: 13px;
    background: #f4f4f4;
    padding: 5px;
    border-radius: 3px;
    overflow-x: auto;
}
.pagination {
    margin: 20px 0;
    text-align: center;
}
.pagination a, .pagination span {
    display: inline-block;
    padding: 8px 12px;
    margin: 0 2px;
    border: 1px solid #ddd;
    border-radius: 4px;
    text-decoration: none;
    color: #3498db;
}
.pagination a:hover {
    background: #f8f9fa;
}
.pagination .current-page {
    background: #3498db;
    color: white;
    border-color: #3498db;
}
.page-size-selector {
    margin: 15px 0;
    padding: 10px;
    background: #f8f9fa;
    border-radius: 4px;
}
.page-size-selector a {
    display: inline-block;
    padding: 5px 10px;
    margin: 0 3px;
    border: 1px solid #ddd;
    border-radius: 3px;
    text-decoration: none;
    color: #3498db;
}
.page-size-selector a:hover {
    background: #e9ecef;
}
.page-size-selector .current-page {
    background: #3498db;
    color: white;
    border-color: #3498db;
}
.footer {
    margin-top: 30px;
    padding-top: 20px;
    border-top: 1px solid #ddd;
    text-align: center;
    color: #666;
    font-size: 14px;
}
hr {
    border: none;
    border-top: 1px solid #ddd;
    margin: 20px 0;
}
'''
    
    def format_size(self, size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    
    def format_time(self, timestamp: float) -> str:
        from datetime import datetime
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime('%Y-%m-%d %H:%M')


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    import argparse
    global ROOT_DIR, PORT, HOST
    
    parser = argparse.ArgumentParser(description='HTTP File Server with directory listing and search')
    parser.add_argument('-p', '--port', type=int, default=PORT, help=f'Port number (default: {PORT})')
    parser.add_argument('--host', type=str, default=HOST, 
                        help=f'Host address to bind (default: {HOST}, use 0.0.0.0 for all interfaces)')
    parser.add_argument('-d', '--directory', type=str, default=os.getcwd(),
                        help='Root directory to serve (default: current directory)')
    
    args = parser.parse_args()
    ROOT_DIR = os.path.abspath(args.directory)
    PORT = args.port
    HOST = args.host
    
    os.chdir(ROOT_DIR)
    
    with ThreadedTCPServer((HOST, PORT), FileServerHandler) as httpd:
        print(f"Serving directory: {ROOT_DIR}")
        if HOST == '0.0.0.0':
            print(f"Server running at: http://localhost:{PORT}/ (listening on all interfaces)")
        else:
            print(f"Server running at: http://{HOST}:{PORT}/")
        print("Press Ctrl+C to stop the server")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == '__main__':
    main()

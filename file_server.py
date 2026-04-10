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
import hmac
import hashlib
import base64
import time
import secrets
import traceback
from datetime import datetime, timedelta

PORT = 8000
HOST = '127.0.0.1'
ROOT_DIR = os.getcwd()
DEFAULT_PAGE_SIZE = 20
PAGE_SIZES = [20, 50, 100, 'all']

AUTH_ENABLED = False
USERNAME = None
PASSWORD = None

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
    '.sql', '.sh', '.bash', '.json', '.yaml', '.yml',
    '.css', '.toml', '.ini', '.conf', '.cfg', '.env'
}

IMAGE_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.ico', '.webp', '.tiff', '.tif'
}

VIDEO_EXTENSIONS = {
    '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm', '.m4v', '.3gp'
}

BROWSER_EXTENSIONS = {
    '.html', '.htm', '.xml', '.xhtml'
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
    
    def check_auth(self) -> tuple:
        if not AUTH_ENABLED:
            return (True, None)
        
        auth_header = self.headers.get('Authorization')
        if auth_header and auth_header.startswith('Basic '):
            try:
                encoded_credentials = auth_header[6:]
                decoded = base64.b64decode(encoded_credentials).decode('utf-8')
                username, password = decoded.split(':', 1)
                if username == USERNAME and password == PASSWORD:
                    return (True, {'user': username, 'expire': None})
            except:
                pass
        
        cookie = self.headers.get('Cookie')
        if cookie:
            result = self.verify_cookie(cookie)
            if result:
                return (True, result)
        
        return (False, None)
    
    def verify_cookie(self, cookie_str: str) -> dict:
        cookies = {}
        for part in cookie_str.split(';'):
            part = part.strip()
            if '=' in part:
                key, value = part.split('=', 1)
                cookies[key.strip()] = value.strip()
        
        auth_cookie = cookies.get('auth')
        if not auth_cookie:
            return None
        
        try:
            params = {}
            for pair in auth_cookie.split('&'):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    params[key] = value
            
            user = params.get('user')
            expire_str = params.get('expire')
            rand = params.get('rand')
            sig = params.get('sig')
            
            if not all([user, expire_str, rand, sig]):
                return None
            
            if user != USERNAME:
                return None
            
            expire_time = datetime.strptime(expire_str, '%Y%m%d-%H%M%S')
            if datetime.now() > expire_time:
                return None
            
            data_to_sign = f'user={user}&expire={expire_str}&rand={rand}'
            expected_sig = hmac.new(
                PASSWORD.encode('utf-8'),
                data_to_sign.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(sig, expected_sig):
                return None
            
            return {'user': user, 'expire': expire_str}
        except:
            return None
    
    def generate_cookie(self, duration_minutes: int) -> str:
        expire_time = datetime.now() + timedelta(minutes=duration_minutes)
        expire_str = expire_time.strftime('%Y%m%d-%H%M%S')
        rand = secrets.token_hex(16)
        
        data_to_sign = f'user={USERNAME}&expire={expire_str}&rand={rand}'
        sig = hmac.new(
            PASSWORD.encode('utf-8'),
            data_to_sign.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return f'{data_to_sign}&sig={sig}'
    
    def serve_login_page(self, error_msg: str = ''):
        current_url = urllib.parse.unquote(self.path)
        
        html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>登录</title>
<style>
{self.get_css_styles()}
.login-container {{
    max-width: 400px;
    margin: 100px auto;
    padding: 40px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}}
.login-container h2 {{
    text-align: center;
    color: #2c3e50;
    margin-bottom: 30px;
}}
.login-form {{
    display: flex;
    flex-direction: column;
    gap: 20px;
}}
.form-group {{
    display: flex;
    flex-direction: column;
    gap: 8px;
}}
.form-group label {{
    font-weight: 600;
    color: #333;
}}
.form-group input, .form-group select {{
    padding: 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 14px;
}}
.form-group input:focus, .form-group select:focus {{
    outline: none;
    border-color: #3498db;
}}
.error-msg {{
    color: #e74c3c;
    background: #fdf2f2;
    padding: 10px;
    border-radius: 4px;
    text-align: center;
}}
.btn-login {{
    padding: 12px;
    background: #3498db;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 16px;
    cursor: pointer;
    margin-top: 10px;
}}
.btn-login:hover {{
    background: #2980b9;
}}
.current-url {{
    text-align: center;
    color: #666;
    font-size: 13px;
    margin-top: 20px;
    word-break: break-all;
}}
</style>
</head>
<body>
<div class="container">
<div class="login-container">
<h2>身份验证</h2>
{'<div class="error-msg">' + html.escape(error_msg) + '</div>' if error_msg else ''}
<form method="POST" class="login-form">
<input type="hidden" name="redirect" value="{html.escape(current_url)}">
<div class="form-group">
<label for="username">用户名</label>
<input type="text" id="username" name="username" required autofocus>
</div>
<div class="form-group">
<label for="password">密码</label>
<input type="password" id="password" name="password" required>
</div>
<div class="form-group">
<label for="duration">会话时长</label>
<select id="duration" name="duration">
<option value="60">1 小时</option>
<option value="480">8 小时</option>
<option value="1440">1 天</option>
<option value="10080">1 周</option>
<option value="43200">30 天</option>
</select>
</div>
<button type="submit" class="btn-login">登录</button>
</form>
<p class="current-url">访问地址: {html.escape(current_url)}</p>
</div>
</div>
</body>
</html>'''
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(html_content.encode('utf-8')))
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def do_POST(self):
        if not AUTH_ENABLED:
            self.send_error_page(405, "Method Not Allowed", "POST 方法不被允许。")
            return
        
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        params = urllib.parse.parse_qs(post_data)
        
        username = params.get('username', [''])[0]
        password = params.get('password', [''])[0]
        duration = int(params.get('duration', ['60'])[0])
        redirect = params.get('redirect', ['/'])[0]
        
        if username == USERNAME and password == PASSWORD:
            cookie_value = self.generate_cookie(duration)
            self.send_response(302)
            self.send_header('Location', redirect)
            self.send_header('Set-Cookie', f'auth={cookie_value}; Path=/; HttpOnly')
            self.end_headers()
        else:
            self.serve_login_page('用户名或密码错误')
    
    def handle_logout(self, current_path: str):
        self.send_response(302)
        self.send_header('Location', current_path)
        self.send_header('Set-Cookie', 'auth=; Path=/; HttpOnly; Expires=Thu, 01 Jan 1970 00:00:00 GMT')
        self.end_headers()
    
    def do_GET(self):
        auth_result = self.check_auth()
        if AUTH_ENABLED and not auth_result[0]:
            self.serve_login_page()
            return
        
        self.auth_info = auth_result[1]
        
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)
        
        if 'logout' in query_params:
            self.handle_logout(parsed_path.path)
            return
        
        if 'search' in query_params:
            self.handle_search(query_params, parsed_path.path)
        elif 'content_search' in query_params:
            self.handle_content_search(query_params, parsed_path.path)
        else:
            path = urllib.parse.unquote(parsed_path.path)
            full_path = os.path.normpath(os.path.join(self.root_dir, path.lstrip('/')))
            
            if not full_path.startswith(self.root_dir):
                self.send_error_page(403, "Forbidden", "您没有权限访问此资源。")
                return
            
            if os.path.islink(full_path):
                real_path = os.path.realpath(full_path)
                if not real_path.startswith(os.path.realpath(self.root_dir)):
                    self.send_error_page(403, "Forbidden", "符号链接指向顶级目录之外，访问被拒绝。")
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
                if 'raw' in query_params:
                    self.serve_raw_file(full_path)
                else:
                    ext = os.path.splitext(full_path)[1].lower()
                    if full_path.endswith('.md'):
                        self.serve_markdown(full_path)
                    elif ext in CODE_EXTENSIONS:
                        self.serve_code_file(full_path)
                    elif ext in IMAGE_EXTENSIONS or ext in VIDEO_EXTENSIONS or ext in ['.html', '.htm', '.xml']:
                        super().do_GET()
                    elif ext in TEXT_EXTENSIONS:
                        self.serve_text_file(full_path)
                    else:
                        self.serve_unknown_file(full_path)
            else:
                self.send_error_page(404, "Not Found", "请求的资源不存在。")
    
    def generate_breadcrumb(self, web_path: str) -> str:
        parts = web_path.strip('/').split('/')
        breadcrumb_parts = ['<a href="/">🏠 Home</a>']
        
        current_path = ''
        for i, part in enumerate(parts):
            if not part:
                continue
            current_path += '/' + part
            if i == len(parts) - 1:
                breadcrumb_parts.append(f'<span class="breadcrumb-current">{html.escape(part)}</span>')
            else:
                breadcrumb_parts.append(f'<a href="{html.escape(current_path)}/">{html.escape(part)}</a>')
        
        return ' <span class="breadcrumb-separator">/</span> '.join(breadcrumb_parts)
    
    def serve_code_file(self, file_path: str):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
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
            self.send_error_page(404, "Not Found", "请求的文件不存在。")
    
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
    
    def serve_text_file(self, file_path: str):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            rel_path = os.path.relpath(file_path, self.root_dir)
            
            html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(rel_path)}</title>
<style>
{self.get_css_styles()}
.text-container {{
    max-width: 100%;
    margin: 0;
    padding: 20px;
    background: #f6f8fa;
}}
.text-header {{
    background: #fff;
    padding: 10px 15px;
    border: 1px solid #e1e4e8;
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.text-header h2 {{
    margin: 0;
    font-size: 16px;
    color: #24292e;
}}
.text-header .file-info {{
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
    font-family: 'Courier New', 'Monaco', monospace;
    font-size: 13px;
    line-height: 1.6;
    white-space: pre-wrap;
    word-wrap: break-word;
}}
</style>
</head>
<body>
<div class="container">
<p><a href="javascript:history.back()">← 返回</a></p>
<div class="text-container">
<div class="text-header">
<h2>{html.escape(os.path.basename(file_path))}</h2>
<span class="file-info">{html.escape(rel_path)}</span>
</div>
<pre><code>{html.escape(content)}</code></pre>
</div>
</div>
</body>
</html>'''
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', len(html_content.encode('utf-8')))
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
        except IOError:
            self.send_error_page(404, "Not Found", "请求的文件不存在。")
    
    def serve_unknown_file(self, file_path: str):
        try:
            with open(file_path, 'rb') as f:
                sample = f.read(1000)
            
            non_printable = sum(1 for byte in sample if byte < 32 and byte not in (9, 10, 13))
            non_printable_ratio = non_printable / len(sample) if sample else 0
            
            if non_printable_ratio > 0.1:
                self.serve_download_prompt(file_path)
            else:
                try:
                    content = sample.decode('utf-8') + (open(file_path, 'r', encoding='utf-8', errors='replace').read()[1000:] if os.path.getsize(file_path) > 1000 else '')
                    rel_path = os.path.relpath(file_path, self.root_dir)
                    
                    html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(rel_path)}</title>
<style>
{self.get_css_styles()}
.text-container {{
    max-width: 100%;
    margin: 0;
    padding: 20px;
    background: #f6f8fa;
}}
.text-header {{
    background: #fff;
    padding: 10px 15px;
    border: 1px solid #e1e4e8;
    border-bottom: none;
    border-radius: 6px 6px 0 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.text-header h2 {{
    margin: 0;
    font-size: 16px;
    color: #24292e;
}}
.text-header .file-info {{
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
    font-family: 'Courier New', 'Monaco', monospace;
    font-size: 13px;
    line-height: 1.6;
    white-space: pre-wrap;
    word-wrap: break-word;
}}
</style>
</head>
<body>
<div class="container">
<p><a href="javascript:history.back()">← 返回</a></p>
<div class="text-container">
<div class="text-header">
<h2>{html.escape(os.path.basename(file_path))}</h2>
<span class="file-info">{html.escape(rel_path)}</span>
</div>
<pre><code>{html.escape(content)}</code></pre>
</div>
</div>
</body>
</html>'''
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', len(html_content.encode('utf-8')))
                    self.end_headers()
                    self.wfile.write(html_content.encode('utf-8'))
                except:
                    self.serve_download_prompt(file_path)
        except IOError:
            self.send_error_page(404, "Not Found", "请求的文件不存在。")
    
    def serve_download_prompt(self, file_path: str):
        rel_path = os.path.relpath(file_path, self.root_dir)
        file_size = os.path.getsize(file_path)
        
        html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(rel_path)}</title>
<style>
{self.get_css_styles()}
.download-prompt {{
    max-width: 600px;
    margin: 100px auto;
    padding: 40px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    text-align: center;
}}
.download-prompt h2 {{
    color: #2c3e50;
    margin-bottom: 20px;
}}
.download-prompt p {{
    color: #666;
    margin-bottom: 30px;
}}
.download-prompt .file-info {{
    background: #f8f9fa;
    padding: 15px;
    border-radius: 5px;
    margin-bottom: 20px;
}}
.download-prompt .btn-group {{
    display: flex;
    gap: 10px;
    justify-content: center;
}}
.download-prompt .btn {{
    padding: 12px 30px;
    font-size: 14px;
}}
</style>
</head>
<body>
<div class="container">
<div class="download-prompt">
<h2>文件预览</h2>
<div class="file-info">
<p><strong>{html.escape(os.path.basename(file_path))}</strong></p>
<p>大小: {self.format_size(file_size)}</p>
</div>
<p>此文件可能不是纯文本文件，是否下载？</p>
<div class="btn-group">
<a href="{html.escape('/' + rel_path.replace(os.sep, '/'))}?raw=1" class="btn">下载文件</a>
<a href="javascript:history.back()" class="btn btn-secondary">返回</a>
</div>
</div>
</div>
</body>
</html>'''
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(html_content.encode('utf-8')))
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def serve_raw_file(self, file_path: str):
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type is None:
                mime_type = 'application/octet-stream'
            
            ext = os.path.splitext(file_path)[1].lower()
            if mime_type.startswith('text/') or ext in TEXT_EXTENSIONS or ext in CODE_EXTENSIONS:
                if 'charset' not in mime_type:
                    mime_type += '; charset=utf-8'
            
            self.send_response(200)
            self.send_header('Content-type', mime_type)
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
        except IOError:
            self.send_error_page(404, "Not Found", "请求的文件不存在。")
    
    def serve_markdown(self, file_path: str):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
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
            self.send_error_page(404, "Not Found", "请求的文件不存在。")
    
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
    
    def send_error_page(self, code: int, title: str, message: str):
        html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Error {code}: {html.escape(title)}</title>
<style>
{self.get_css_styles()}
.error-container {{
    max-width: 600px;
    margin: 100px auto;
    padding: 40px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    text-align: center;
}}
.error-code {{
    font-size: 72px;
    font-weight: bold;
    color: #e74c3c;
    margin-bottom: 20px;
}}
.error-title {{
    font-size: 24px;
    color: #2c3e50;
    margin-bottom: 15px;
}}
.error-message {{
    color: #666;
    margin-bottom: 30px;
    font-size: 16px;
}}
.error-actions {{
    display: flex;
    gap: 10px;
    justify-content: center;
}}
.error-actions .btn {{
    padding: 12px 30px;
    font-size: 14px;
}}
</style>
</head>
<body>
<div class="container">
<div class="error-container">
<div class="error-code">{code}</div>
<h1 class="error-title">{html.escape(title)}</h1>
<p class="error-message">{html.escape(message)}</p>
<div class="error-actions">
<a href="javascript:history.back()" class="btn btn-secondary">返回上一页</a>
<a href="/" class="btn">返回首页</a>
</div>
</div>
</div>
</body>
</html>'''
        
        self.send_response(code)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(html_content.encode('utf-8')))
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
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
            self.send_error_page(403, "Permission Denied", "权限不足，无法访问此目录。")
    
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
        
        breadcrumb_html = self.generate_breadcrumb(web_path)
        
        user_info_html = ''
        if AUTH_ENABLED and hasattr(self, 'auth_info') and self.auth_info:
            user = self.auth_info.get('user', '')
            expire = self.auth_info.get('expire', '')
            if expire:
                expire_display = f'{expire[:4]}-{expire[4:6]}-{expire[6:8]} {expire[9:11]}:{expire[11:13]}:{expire[13:15]}'
            else:
                expire_display = '--'
            logout_url = f'{web_path}?logout=1'
            user_info_html = f'''<div class="user-info-bar">
<span class="user-name">👤 {html.escape(user)}</span>
<span class="user-expire">到期: {expire_display}</span>
<a href="{html.escape(logout_url)}" class="logout-btn">注销</a>
</div>'''
        
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
            user_info_html,
            f'<div class="breadcrumb">{breadcrumb_html}</div>',
            '<div class="search-box">',
            '<form method="GET" class="search-form">',
            '<div class="search-row">',
            '<input type="text" name="search" placeholder="文件名搜索" class="search-input">',
            '<label class="search-option"><input type="checkbox" name="ignore_case" value="1" checked> 忽略大小写</label>',
            '<label class="search-option"><input type="checkbox" name="use_regex" value="1"> 正则表达式</label>',
            '<button type="submit" class="btn search-btn">搜索文件名</button>',
            '</div>',
            '</form>',
            '<form method="GET" class="search-form">',
            '<div class="search-row">',
            '<input type="text" name="content_search" placeholder="文件内容搜索" class="search-input">',
            '<label class="search-option"><input type="checkbox" name="ignore_case" value="1" checked> 忽略大小写</label>',
            '<label class="search-option"><input type="checkbox" name="use_regex" value="1"> 正则表达式</label>',
            '<button type="submit" class="btn btn-secondary search-btn">搜索内容</button>',
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
                raw_link = ''
            else:
                display_name = name
                size_str = self.format_size(size)
                raw_link = f' <a href="{html.escape(link_path)}?raw=1" class="raw-link" title="查看原始文件">📄</a>'
            
            mtime_str = self.format_time(mtime)
            
            html_parts.append(
                f'<tr><td><a href="{html.escape(link_path)}">{html.escape(display_name)}</a>{raw_link}</td>'
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
        
        ignore_case = 'ignore_case' in query_params
        use_regex = 'use_regex' in query_params
        
        if use_regex:
            flags = re.IGNORECASE if ignore_case else 0
            try:
                pattern = re.compile(search_term, flags)
            except re.error:
                pattern = re.compile(re.escape(search_term), flags)
        else:
            if ignore_case:
                pattern = re.compile(re.escape(search_term), re.IGNORECASE)
            else:
                pattern = re.compile(re.escape(search_term))
        
        results = self.search_filenames(base_path, pattern)
        page = int(query_params.get('page', ['1'])[0])
        page_size = query_params.get('page_size', [str(DEFAULT_PAGE_SIZE)])[0]
        
        if page_size == 'all':
            page_size = len(results)
        else:
            page_size = int(page_size)
        
        html_content = self.generate_search_results_html(
            search_term, results, page, page_size, 'filename', base_path,
            ignore_case, use_regex
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
        
        ignore_case = 'ignore_case' in query_params
        use_regex = 'use_regex' in query_params
        
        if use_regex:
            flags = re.IGNORECASE if ignore_case else 0
            try:
                pattern = re.compile(search_term, flags)
            except re.error:
                pattern = re.compile(re.escape(search_term), flags)
        else:
            if ignore_case:
                pattern = re.compile(re.escape(search_term), re.IGNORECASE)
            else:
                pattern = re.compile(re.escape(search_term))
        
        results = self.search_file_contents(base_path, pattern)
        page = int(query_params.get('page', ['1'])[0])
        page_size = query_params.get('page_size', [str(DEFAULT_PAGE_SIZE)])[0]
        
        if page_size == 'all':
            page_size = len(results)
        else:
            page_size = int(page_size)
        
        html_content = self.generate_search_results_html(
            search_term, results, page, page_size, 'content', base_path,
            ignore_case, use_regex
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
            cmd = ['rg', '-n', '--no-heading', '--with-filename']
            if pattern.flags & re.IGNORECASE:
                cmd.append('-i')
            cmd.extend([pattern.pattern, search_dir])
            proc = subprocess.run(cmd, capture_output=True, encoding='utf-8', errors='replace', timeout=30)
            
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
        except (subprocess.TimeoutExpired, Exception) as e:
            print(f"[search_with_ripgrep] Error: {e}")
            traceback.print_exc()
        
        return results
    
    def search_with_grep(self, search_dir: str, pattern: re.Pattern) -> List[SearchResult]:
        results = []
        try:
            cmd = ['grep', '-r', '-n', '-E']
            if pattern.flags & re.IGNORECASE:
                cmd.append('-i')
            cmd.extend([pattern.pattern, search_dir])
            proc = subprocess.run(cmd, capture_output=True, encoding='utf-8', errors='replace', timeout=30)
            
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
        except (subprocess.TimeoutExpired, Exception) as e:
            print(f"[search_with_grep] Error: {e}")
            traceback.print_exc()
        
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
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
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
        except Exception as e:
            print(f"[is_text_file] Error checking {file_path}: {e}")
            return False
    
    def generate_search_results_html(self, search_term: str, results: List, page: int,
                                     page_size: int, search_type: str, base_path: str,
                                     ignore_case: bool = True, use_regex: bool = False) -> str:
        MAX_RESULTS = 5000
        total_results = len(results)
        results_limited = total_results > MAX_RESULTS
        
        if results_limited:
            results = results[:MAX_RESULTS]
            total_results = MAX_RESULTS
        
        total_pages = (total_results + page_size - 1) // page_size if page_size > 0 else 1
        page = max(1, min(page, total_pages))
        
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_results = results[start_idx:end_idx]
        
        search_param = 'search' if search_type == 'filename' else 'content_search'
        
        def highlight_text(text: str, term: str) -> str:
            try:
                if use_regex:
                    pattern_str = f'({term})'
                else:
                    pattern_str = f'({re.escape(term)})'
                
                if ignore_case:
                    pattern = re.compile(pattern_str, re.IGNORECASE)
                else:
                    pattern = re.compile(pattern_str)
                
                escaped_text = html.escape(text)
                return pattern.sub(r'<span class="highlight">\1</span>', escaped_text)
            except:
                return html.escape(text)
        
        pagination_html = self.generate_pagination(search_param, search_term, page, total_pages, page_size, total_results, ignore_case, use_regex)
        
        limit_warning = ''
        if results_limited:
            limit_warning = ' <span class="limit-warning">(结果已限制为 5000 条)</span>'
        
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
            '<div class="search-header">',
            f'<h1>搜索结果: {html.escape(search_term)}{limit_warning}</h1>',
            f'<a href="{html.escape(base_path)}" class="back-link">返回目录</a>',
            '</div>',
            f'<p>找到 {total_results} 个结果 (第 {page}/{total_pages} 页)</p>',
        ]
        
        if total_pages > 1:
            html_parts.append(pagination_html)
        
        if search_type == 'filename':
            html_parts.append('<div class="search-results">')
            for idx, result in enumerate(page_results, start=start_idx + 1):
                link_path = '/' + result.replace(os.sep, '/')
                highlighted = highlight_text(result, search_term)
                html_parts.append(
                    f'<div class="result-item"><span class="result-number">{idx}.</span> <a href="{html.escape(link_path)}">{highlighted}</a></div>'
                )
            html_parts.append('</div>')
        else:
            html_parts.append('<div class="content-search-results">')
            for idx, result in enumerate(page_results, start=start_idx + 1):
                link_path = '/' + result.file_path.replace(os.sep, '/')
                html_parts.append('<div class="result-item">')
                html_parts.append(
                    f'<span class="result-number">{idx}.</span> <a href="{html.escape(link_path)}">{html.escape(result.file_path)}</a>'
                )
                highlighted_content = highlight_text(result.line_content, search_term)
                html_parts.append(
                    f'<div class="result-line">Line {result.line_number}: {highlighted_content}</div>'
                )
                html_parts.append('</div>')
            html_parts.append('</div>')
        
        if total_pages > 1:
            html_parts.append(pagination_html)
        
        html_parts.extend([
            '<hr>',
            f'<p><a href="{html.escape(base_path)}">返回目录</a></p>',
            '</div>',
            '</body>',
            '</html>'
        ])
        
        return '\n'.join(html_parts)
    
    def generate_pagination(self, search_param: str, search_term: str, page: int, total_pages: int, page_size: int, total_results: int, ignore_case: bool = True, use_regex: bool = False) -> str:
        extra_params = f'&ignore_case={"1" if ignore_case else "0"}&use_regex={"1" if use_regex else "0"}'
        html_parts = ['<div class="pagination">']
        
        if page > 1:
            html_parts.append(
                f'<a href="?{search_param}={urllib.parse.quote(search_term)}&page=1&page_size={page_size}{extra_params}">首页</a> '
            )
            html_parts.append(
                f'<a href="?{search_param}={urllib.parse.quote(search_term)}&page={page-1}&page_size={page_size}{extra_params}">上一页</a> '
            )
        
        start_page = max(1, page - 2)
        end_page = min(total_pages + 1, page + 3)
        
        if start_page > 1:
            html_parts.append('<span>...</span> ')
        
        for p in range(start_page, end_page):
            if p == page:
                html_parts.append(f'<span class="current-page">{p}</span> ')
            else:
                html_parts.append(
                    f'<a href="?{search_param}={urllib.parse.quote(search_term)}&page={p}&page_size={page_size}{extra_params}">{p}</a> '
                )
        
        if end_page < total_pages + 1:
            html_parts.append('<span>...</span> ')
        
        if page < total_pages:
            html_parts.append(
                f'<a href="?{search_param}={urllib.parse.quote(search_term)}&page={page+1}&page_size={page_size}{extra_params}">下一页</a> '
            )
            html_parts.append(
                f'<a href="?{search_param}={urllib.parse.quote(search_term)}&page={total_pages}&page_size={page_size}{extra_params}">末页</a> '
            )
        
        html_parts.append(
            f'<span class="page-jump"><select onchange="window.location.href=\'?{search_param}={urllib.parse.quote(search_term)}&page=\'+this.value+\'&page_size={page_size}{extra_params}\'">'
        )
        
        for p in range(1, total_pages + 1):
            selected = ' selected' if p == page else ''
            html_parts.append(f'<option value="{p}"{selected}>第 {p} 页</option>')
        
        html_parts.append('</select></span>')
        
        if total_results > 20:
            html_parts.append('<span class="page-size-selector-inline">每页显示: ')
            for size in PAGE_SIZES:
                if size == 'all':
                    if total_results > page_size:
                        if size == page_size or (size == 'all' and page_size == total_results):
                            html_parts.append(f'<span class="current-page">全部</span> ')
                        else:
                            html_parts.append(
                                f'<a href="?{search_param}={urllib.parse.quote(search_term)}&page=1&page_size=all{extra_params}">全部</a> '
                            )
                else:
                    if total_results > size:
                        if size == page_size:
                            html_parts.append(f'<span class="current-page">{size}</span> ')
                        else:
                            html_parts.append(
                                f'<a href="?{search_param}={urllib.parse.quote(search_term)}&page=1&page_size={size}{extra_params}">{size}</a> '
                            )
            html_parts.append('</span>')
        
        html_parts.append('</div>')
        
        return '\n'.join(html_parts)
    
    def serve_markdown(self, file_path: str):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            rel_path = os.path.relpath(file_path, self.root_dir)
            dir_path = os.path.dirname(rel_path)
            if dir_path:
                back_link = '/' + dir_path.replace(os.sep, '/') + '/'
            else:
                back_link = '/'
            
            processed_content = self.process_markdown_front_matter(content)
            processed_content = self.process_mermaid_blocks(processed_content)
            
            html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(rel_path)}</title>
</head>
<body>
<p><a href="{html.escape(back_link)}">← 返回目录</a></p>
{processed_content}
<!-- Markdeep: --><style class="fallback">body{{visibility:hidden;white-space:pre;font-family:monospace}}</style><script src="markdeep.min.js" charset="utf-8"></script><script src="https://morgan3d.github.io/markdeep/latest/markdeep.min.js" charset="utf-8"></script><script>window.alreadyProcessedMarkdeep||(document.body.style.visibility="visible")</script>
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
<script>mermaid.initialize({{startOnLoad:true,theme:'default'}});</script>
</body>
</html>'''
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', len(html_content.encode('utf-8')))
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
        except IOError:
            self.send_error_page(404, "Not Found", "请求的文件不存在。")
    
    def process_markdown_front_matter(self, content: str) -> str:
        if not content.startswith('---'):
            return content
        
        lines = content.split('\n')
        if len(lines) < 2:
            return content
        
        end_index = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                end_index = i
                break
        
        if end_index == -1:
            return content
        
        front_matter_lines = lines[1:end_index]
        rest_content = '\n'.join(lines[end_index + 1:])
        
        title = None
        for line in front_matter_lines:
            if line.strip().startswith('title:'):
                title = line.split(':', 1)[1].strip().strip('"\'')
                break
        
        yaml_block = '```yaml\n' + '\n'.join(front_matter_lines) + '\n```\n\n'
        
        if title:
            yaml_block = f'# {title}\n\n' + yaml_block
        
        return yaml_block + rest_content
    
    def process_mermaid_blocks(self, content: str) -> str:
        def replace_mermaid(match):
            mermaid_code = match.group(1)
            return f'<pre class="mermaid">\n{mermaid_code}\n</pre>'
        
        pattern = r'```mermaid\s*\n(.*?)```'
        return re.sub(pattern, replace_mermaid, content, flags=re.DOTALL)
    
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
    min-width: 200px;
}
.search-option {
    display: flex;
    align-items: center;
    margin: 0 10px;
    font-size: 13px;
    white-space: nowrap;
}
.search-option input {
    margin-right: 5px;
}
.search-btn {
    min-width: 120px;
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
.raw-link {
    font-size: 16px;
    margin-left: 8px;
    opacity: 0.6;
    text-decoration: none;
}
.raw-link:hover {
    opacity: 1;
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
.page-jump {
    margin-left: 10px;
    padding: 0 10px;
}
.page-jump select {
    padding: 5px 10px;
    border: 1px solid #ddd;
    border-radius: 3px;
    background: white;
    cursor: pointer;
    font-size: 14px;
}
.page-size-selector-inline {
    margin-left: 20px;
    padding-left: 20px;
    border-left: 1px solid #ddd;
}
.page-size-selector-inline a,
.page-size-selector-inline span {
    display: inline-block;
    padding: 8px 12px;
    margin: 0 2px;
    border: 1px solid #ddd;
    border-radius: 4px;
    text-decoration: none;
    color: #3498db;
}
.page-size-selector-inline a:hover {
    background: #e9ecef;
}
.page-size-selector-inline .current-page {
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
.breadcrumb {
    padding: 15px 0;
    margin-bottom: 20px;
    font-size: 16px;
    color: #666;
}
.breadcrumb a {
    color: #3498db;
    text-decoration: none;
}
.breadcrumb a:hover {
    text-decoration: underline;
}
.breadcrumb-separator {
    color: #999;
    margin: 0 8px;
}
.breadcrumb-current {
    color: #2c3e50;
    font-weight: 600;
}
.highlight {
    background-color: #fff3cd;
    padding: 2px 4px;
    border-radius: 3px;
}
.search-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}
.search-header h1 {
    margin: 0;
    border: none;
    padding: 0;
}
.back-link {
    color: #3498db;
    text-decoration: none;
    font-size: 14px;
}
.back-link:hover {
    text-decoration: underline;
}
.limit-warning {
    color: #e67e22;
    font-size: 14px;
    font-weight: normal;
}
.result-number {
    font-weight: 600;
    color: #2c3e50;
    margin-bottom: 5px;
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
.user-info-bar {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 20px;
    padding: 10px 15px;
    background: #f8f9fa;
    border-radius: 5px;
    margin-bottom: 15px;
    font-size: 14px;
}
.user-name {
    font-weight: 600;
    color: #2c3e50;
}
.user-expire {
    color: #666;
}
.logout-btn {
    padding: 5px 15px;
    background: #e74c3c;
    color: white;
    text-decoration: none;
    border-radius: 4px;
    font-size: 13px;
}
.logout-btn:hover {
    background: #c0392b;
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
        return dt.strftime('%Y-%m-%d %H:%M:%S')


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    import argparse
    import getpass
    global ROOT_DIR, PORT, HOST, AUTH_ENABLED, USERNAME, PASSWORD
    
    parser = argparse.ArgumentParser(description='HTTP File Server with directory listing and search')
    parser.add_argument('-p', '--port', type=int, default=PORT, help=f'Port number (default: {PORT})')
    parser.add_argument('--host', type=str, default=HOST, 
                        help=f'Host address to bind (default: {HOST}, use 0.0.0.0 for all interfaces)')
    parser.add_argument('-d', '--directory', type=str, default=os.getcwd(),
                        help='Root directory to serve (default: current directory)')
    parser.add_argument('--username', type=str, help='Username for authentication')
    parser.add_argument('--password', type=str, help='Password for authentication (or set PASSWORD env var)')
    
    args = parser.parse_args()
    
    if args.username:
        AUTH_ENABLED = True
        USERNAME = args.username
        PASSWORD = args.password or os.environ.get('PASSWORD', '')
        
        if not PASSWORD:
            PASSWORD = getpass.getpass('Enter password: ')
    
    ROOT_DIR = os.path.abspath(args.directory)
    PORT = args.port
    HOST = args.host
    
    os.chdir(ROOT_DIR)
    
    with ThreadedTCPServer((HOST, PORT), FileServerHandler) as httpd:
        print(f"Serving directory: {ROOT_DIR}")
        if AUTH_ENABLED:
            print(f"Authentication enabled for user: {USERNAME}")
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

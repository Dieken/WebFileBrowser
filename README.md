# Python HTTP File Server

一个功能丰富的 HTTP 文件服务器，支持目录浏览、文件搜索、Markdown 渲染和代码语法高亮。类似于 Apache mod_autoindex，但具有更多增强功能。

## 特性

### 📁 目录浏览
- 类似 Apache mod_autoindex 风格的目录列表
- 显示文件名、大小、修改时间
- 支持按 Name、Size、Modified 排序（升序/降序）
- 目录优先显示
- 不自动映射 index.html/index.htm/index.md 到根路径

### 🔍 文件搜索
- **文件名搜索**：支持正则表达式，递归搜索所有子目录
- **文件内容搜索**：
  - 优先使用 ripgrep (rg) - 最快的搜索工具
  - Fallback 到 grep - 系统自带工具
  - 最终 fallback 到 Python 实现 - 纯 Python 方案
  - 支持正则表达式
  - 自动识别文本文件

### 📄 搜索结果分页
- 默认每页 20 条结果
- 支持 20、50、100、全部 四种显示模式
- 分页导航，显示当前页码

### 📝 Markdown 渲染
- 点击 .md 文件时自动使用 Markdeep 渲染
- 支持表格、代码块、数学公式等高级特性
- 美观的排版和样式

### 💻 代码语法高亮
- 使用 Highlight.js (v11.9.0) - 最流行的语法高亮库
- 支持 190+ 种编程语言
- GitHub 风格主题
- 行号显示
- 自动语言检测

### 🎨 其他特性
- 多线程支持，可同时处理多个请求
- 响应式设计，支持移动设备
- 安全路径检查，防止目录遍历攻击
- 美观的 UI 设计
- 无外部依赖，仅使用 Python 标准库

### 🔐 身份认证
- 支持 HTTP Basic Auth 和 Cookie 两种认证方式
- Cookie 认证使用 HMAC-SHA256 签名，安全可靠
- 可配置会话时长（1小时、8小时、1天、1周、30天）
- 登录页面支持显示当前访问 URL
- 页面右上角显示用户名、到期时间和注销按钮

## 安装

无需安装，只需 Python 3.6+ 即可运行。

```bash
# 检查 Python 版本
python3 --version
```

## 使用方法

### 基本用法

```bash
# 在当前目录启动服务器，默认端口 8000，监听 localhost
python3 file_server.py

# 指定端口
python3 file_server.py -p 9000

# 指定目录
python3 file_server.py -d /path/to/directory

# 监听所有网络接口（允许外部访问）
python3 file_server.py --host 0.0.0.0

# 组合使用
python3 file_server.py -p 9000 --host 0.0.0.0 -d /path/to/directory
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-p, --port` | 端口号 | 8000 |
| `--host` | 监听地址 | 127.0.0.1 (localhost) |
| `-d, --directory` | 服务目录 | 当前目录 |
| `--username` | 用户名（开启认证） | 无 |
| `--password` | 密码（或设置环境变量 PASSWORD） | 无 |
| `--theme` | Markdeep 主题（用于 .md 文件渲染） | default |

### 监听地址说明

- **127.0.0.1** (默认)：仅本机访问，最安全
- **0.0.0.0**：监听所有网络接口，允许局域网或外网访问（需注意安全）

### 身份认证

#### 启用认证

```bash
# 方式1：命令行指定用户名和密码
python3 file_server.py --username admin --password secret

# 方式2：从环境变量获取密码
export PASSWORD=secret
python3 file_server.py --username admin

# 方式3：启动时输入密码（输入时不显示）
python3 file_server.py --username admin
# Enter password: (输入密码)
```

#### 认证方式

1. **HTTP Basic Auth**：在请求头添加 `Authorization: Basic base64(username:password)`
   - 适用于 API 调用和自动化脚本
   - 无过期时间，每次请求都需要携带

2. **Cookie 认证**：通过登录页面获取 Cookie
   - 适用于浏览器访问
   - 支持可配置的会话时长
   - Cookie 格式：`user=xxx&expire=YYYYmmdd-HHMMSS&rand=xxx&sig=SIGNATURE`
   - 签名使用 HMAC-SHA256，以密码为密钥

#### 登录页面

- 显示当前访问的 URL
- 用户名和密码输入框
- 会话时长选择：1小时、8小时、1天、1周、30天
- 登录成功后自动跳转到原 URL

#### 用户信息栏

认证成功后，页面右上角显示：
- 用户名
- 到期时间（Cookie 认证显示具体时间，Basic Auth 显示 "--"）
- 注销按钮（点击后清除 Cookie 并重新登录）

## 功能详解

### 目录排序

点击表头 "Name"、"Size"、"Modified" 可按对应字段排序：
- **Name**: 按文件名字母顺序排序
- **Size**: 按文件大小排序
- **Modified**: 按修改时间排序
- 点击同一表头可切换升序/降序
- 目录始终优先显示

### 文件搜索

#### 文件名搜索
- 在搜索框输入文件名或正则表达式
- 支持递归搜索所有子目录
- 示例：
  - `\.py$` - 搜索所有 Python 文件
  - `README` - 搜索包含 README 的文件
  - `test.*\.js` - 搜索 test 开头的 JS 文件

#### 文件内容搜索
- 在内容搜索框输入关键词或正则表达式
- 自动使用最优搜索工具（ripgrep > grep > Python）
- 显示匹配的文件名和行号
- 示例：
  - `import os` - 搜索包含 "import os" 的文件
  - `def.*\(` - 搜索函数定义
  - `TODO|FIXME` - 搜索待办事项

### Markdown 文件

点击 .md 文件会自动使用 Markdeep 渲染，支持：
- 标题、段落、列表
- 代码块和语法高亮
- 表格
- 数学公式
- 图表
- 目录

### Markdeep 主题

通过 `--theme` 参数可以为 Markdown 文件指定不同的 Markdeep 主题：

```bash
# 使用 slate 主题（深色主题）
python3 file_server.py --theme slate

# 使用 latex 主题（类似 LaTeX 论文风格）
python3 file_server.py --theme latex

# 使用本地 CSS 文件作为主题
python3 file_server.py --theme /path/to/custom.css
```

#### 可用主题

| 主题名称 | 说明 |
|---------|------|
| `default` | 默认主题，无额外样式 |
| `api` | API 文档风格 |
| `apidoc` | API 文档风格（另一种） |
| `dark` | 深色主题（另一种） |
| `journal` | 期刊论文风格 |
| `latex` | LaTeX 论文风格 |
| `slate` | 深色主题，适合夜间阅读 |
| `slide` | 幻灯片风格 |
| `website` | 网站风格 |
| `whitepaper` | 白皮书风格，适合正式文档 |
| `PATH` | 本地 CSS 文件路径（自定义主题） |

### 代码文件

以下文件类型会自动应用语法高亮：
- Python (.py)
- JavaScript/TypeScript (.js, .ts, .jsx, .tsx)
- Java (.java)
- C/C++ (.c, .cpp, .h, .hpp)
- Go (.go)
- Rust (.rs)
- Ruby (.rb)
- PHP (.php)
- Shell (.sh, .bash)
- HTML/CSS (.html, .css)
- JSON/XML/YAML (.json, .xml, .yaml, .yml)
- SQL (.sql)
- 以及更多...

## 示例

### 启动服务器

```bash
# 在 ~/Documents 目录启动服务器
python3 file_server.py -d ~/Documents

# 在端口 3000 启动，允许局域网访问
python3 file_server.py -p 3000 --host 0.0.0.0

# 启用认证，允许局域网访问
python3 file_server.py --host 0.0.0.0 --username admin --password secret
```

### 访问服务器

启动后，在浏览器中访问：
- 本地访问：http://localhost:8000/
- 局域网访问（如果使用 --host 0.0.0.0）：http://your-ip:8000/

### 停止服务器

按 `Ctrl+C` 停止服务器。

## 安全建议

1. **默认监听 localhost**：默认配置仅允许本机访问，最安全
2. **谨慎使用 0.0.0.0**：监听所有接口会暴露服务，确保在可信网络中使用
3. **启用认证**：如果需要暴露到网络，强烈建议启用身份认证
4. **不要暴露到公网**：此服务器仅用于本地开发，不建议暴露到公网
5. **路径安全**：已实现路径检查，防止目录遍历攻击
6. **Cookie 安全**：Cookie 设置了 HttpOnly 标志，防止 XSS 攻击窃取

## 技术栈

- **Python 3**：仅使用标准库，无外部依赖
- **Highlight.js**：代码语法高亮
- **Markdeep**：Markdown 渲染

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

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

### 监听地址说明

- **127.0.0.1** (默认)：仅本机访问，最安全
- **0.0.0.0**：监听所有网络接口，允许局域网或外网访问（需注意安全）

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
3. **不要暴露到公网**：此服务器仅用于本地开发，不建议暴露到公网
4. **路径安全**：已实现路径检查，防止目录遍历攻击

## 技术栈

- **Python 3**：仅使用标准库，无外部依赖
- **Highlight.js**：代码语法高亮
- **Markdeep**：Markdown 渲染

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

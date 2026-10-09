# AI剪贴板助手

一个基于Tauri的桌面应用，将LLM变成顺手的基础设施。选中即翻译、即总结。

## ✨ 功能特性

- 🌐 **智能翻译** - 支持多种语言对（中英互译、中日互译等）
- 📝 **自动总结** - 快速提取文本核心内容
- 🎯 **全局热键** - 快捷键触发操作（Ctrl+Shift+V翻译，Ctrl+Shift+S总结）
- 💾 **配置持久化** - 自定义LLM提供商和快捷键
- 🖼️ **系统托盘** - 常驻后台，右键菜单操作

## 🚀 快速开始

### 前置要求

1. **Node.js 16+**
2. **Rust 1.70+**
3. **Visual Studio Build Tools**（Windows）

### 安装Rust工具链

详细安装步骤请查看 [INSTALL_RUST.md](INSTALL_RUST.md)

**快速安装：**
1. 下载 https://rustup.rs/
2. 运行安装程序
3. 重启命令行窗口

### 启动项目

```bash
# 安装依赖
npm install

# 启动开发模式
npm run tauri dev

# 构建生产版本
npm run tauri build
```

## 📁 项目结构

```
ai-clipboard-assistant/
├── src-tauri/          # Rust后端
│   ├── src/
│   │   ├── main.rs     # 主入口
│   │   ├── config.rs   # 配置管理
│   │   ├── tray.rs     # 系统托盘
│   │   ├── clipboard.rs # 剪贴板监听
│   │   ├── llm.rs      # LLM调用
│   │   └── commands.rs # Tauri命令
│   ├── Cargo.toml
│   └── tauri.conf.json
├── src/                # React前端
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── package.json
├── vite.config.ts
└── README.md
```

## ⚙️ 配置说明

配置文件位置：`%APPDATA%\ai-clipboard-assistant\config.ini`

### LLM配置示例

```ini
[llm]
provider = openai
api_key = your_api_key_here
base_url = https://api.openai.com/v1
model = gpt-3.5-turbo

[hotkeys]
translate = Ctrl+Shift+V
summarize = Ctrl+Shift+S

[features]
auto_translate = true
auto_summarize = false
show_popup = true
```

## 🎯 快捷键

- `Ctrl+Shift+V` - 触发翻译
- `Ctrl+Shift+S` - 触发总结

## 📚 文档

- [快速启动指南](QUICKSTART.md)
- [项目总结](PROJECT_SUMMARY.md)
- [Rust安装指南](INSTALL_RUST.md)

## 🔧 支持的LLM提供商

- ✅ OpenAI (GPT-3.5, GPT-4)
- ✅ Azure OpenAI
- ✅ Anthropic (Claude)
- ✅ 本地Ollama
- ✅ DeepSeek
- ✅ 其他兼容OpenAI格式的API

## 🛠️ 技术栈

- **后端**: Rust + Tauri 2.x
- **前端**: React + TypeScript + Vite
- **LLM**: 兼容OpenAI格式的API

## 📝 使用方法

1. **复制文本** - 选中需要翻译或总结的文本并复制到剪贴板
2. **触发操作** - 按下快捷键或点击"翻译"/"总结"按钮
3. **查看结果** - 在应用窗口中查看翻译或总结结果
4. **一键复制** - 点击"复制"按钮将结果复制到剪贴板

## 🚧 开发进度

### 已完成
- ✅ Tauri项目框架
- ✅ 系统托盘功能
- ✅ 剪贴板监听
- ✅ LLM API集成
- ✅ 配置管理
- ✅ 前端UI

### 待完成
- ⏳ 全局热键支持
- ⏳ 悬浮窗界面
- ⏳ 历史记录功能
- ⏳ 图片翻译
- ⏳ 更多语言对支持

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交Issue和Pull Request！

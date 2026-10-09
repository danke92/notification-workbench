# AI剪贴板助手 - 安装和启动指南

## 📋 安装步骤

### 步骤1：安装Rust工具链

**方法A：使用rustup（推荐）**

1. 访问 https://rustup.rs/
2. 下载 rustup-init.exe
3. 双击运行安装程序，按Enter接受默认选项
4. 等待安装完成
5. **重要：重启命令行窗口或计算机**

**验证安装：**
```bash
rustc --version
cargo --version
```

### 步骤2：安装Visual Studio Build Tools（Windows）

1. 访问：https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. 下载并运行 Visual Studio Build Tools
3. 安装时选择"Desktop development with C++"
4. 确保勾选：
   - MSVC v143 - VS 2022 C++ x64/x86 生成工具
   - Windows 10 SDK 或 Windows 11 SDK
5. 点击"安装"
6. **等待安装完成**（可能需要10-30分钟）

### 步骤3：安装项目依赖

```bash
# 进入项目目录
cd C:\Users\LEGION\.zcode\workspace\default\ai-clipboard-assistant

# 安装npm依赖
npm install

# 安装Tauri CLI（如果尚未安装）
npm install -g @tauri-apps/cli
```

### 步骤4：启动项目

```bash
# 启动开发模式
npm run tauri dev
```

## 🎯 启动成功后

应用窗口应该会打开，显示：
- 文本输入区域
- 翻译和总结按钮
- 结果展示区域

## 🔧 配置LLM API

1. 在应用中输入你的LLM API Key
2. 选择LLM提供商（OpenAI、Azure、Ollama等）
3. 选择模型（GPT-3.5、GPT-4等）
4. 点击保存

## 📝 使用示例

1. 复制任意文本到剪贴板
2. 点击"翻译"按钮或按 `Ctrl+Shift+V`
3. 查看翻译结果
4. 点击"复制"按钮将结果复制回剪贴板

## ❓ 常见问题

### Q: 编译失败，提示"cargo: command not found"
A: Rust没有安装或未在PATH中。请按照步骤1重新安装Rust。

### Q: 编译失败，提示"cl.exe not found"
A: Visual Studio Build Tools未正确安装。请按照步骤2重新安装。

### Q: npm run tauri dev 启动后应用不显示
A: 检查浏览器控制台是否有错误信息。

### Q: 翻译功能无法使用
A: 确保已配置正确的LLM API Key和Base URL。

## 📚 更多资源

- [Tauri官方文档](https://tauri.app/)
- [Rust学习资源](https://www.rust-lang.org/learn)
- [React官方文档](https://react.dev/)

## 🎉 完成！

安装完成后，你就可以开始使用AI剪贴板助手了！

有任何问题，请查看项目中的其他文档：
- README.md - 项目说明
- QUICKSTART.md - 快速启动
- PROJECT_SUMMARY.md - 项目总结

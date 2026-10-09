# 安装Rust工具链

## Windows系统安装步骤

### 方法1：使用rustup（推荐）

1. 下载并运行rustup-init.exe
   - 下载地址：https://rustup.rs/

2. 运行安装程序，按照提示完成安装
   - 默认安装即可，推荐选择"Default"

3. 安装完成后，重启命令行窗口

4. 验证安装：
   ```bash
   cargo --version
   rustc --version
   ```

### 方法2：使用Microsoft Build Tools

1. 下载Visual Studio Build Tools
   - 下载地址：https://visualstudio.microsoft.com/visual-cpp-build-tools/

2. 在安装过程中，确保勾选以下组件：
   - "使用C++的桌面开发"
   - "MSVC v143 - VS 2022 C++ x64/x86 生成工具"
   - "Windows 10 SDK" 或 "Windows 11 SDK"

3. 安装完成后重启计算机

## 安装完成后

1. 打开新的命令行窗口
2. 运行以下命令安装Tauri CLI：
   ```bash
   npm install -g @tauri-apps/cli
   ```

3. 返回项目目录并启动：
   ```bash
   cd ai-clipboard-assistant
   npm run tauri dev
   ```

## 常见问题

### Q: 安装后cargo命令找不到？
A: 重启命令行窗口或计算机

### Q: 编译失败？
A: 确保安装了Visual Studio Build Tools，并且选择了正确的C++组件

### Q: 需要什么版本？
A: Rust 1.70+，Node.js 16+

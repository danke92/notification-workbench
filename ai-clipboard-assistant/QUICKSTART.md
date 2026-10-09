# 快速启动指南

## 第一步：安装依赖

```bash
# 安装npm依赖
npm install

# 安装Tauri CLI（如果尚未安装）
npm install -g @tauri-apps/cli
```

## 第二步：构建项目

```bash
# 构建生产版本
npm run tauri build
```

构建完成后，可执行文件位于：
- `src-tauri/target/release/bundle/msi/` - Windows安装包
- `src-tauri/target/release/bundle/portable/` - 便携版

## 第三步：运行开发模式

```bash
# 启动开发服务器（带热重载）
npm run tauri dev
```

## 第四步：配置LLM API

1. 打开应用，进入设置页面
2. 输入你的LLM API Key
3. 选择LLM提供商和模型
4. 保存配置

## 常见问题

### Q: 构建失败怎么办？
A: 确保已安装：
- Node.js 16+
- Rust 1.70+
- Visual Studio Build Tools（Windows）

### Q: LLM API调用失败？
A: 检查：
- API Key是否正确
- Base URL是否正确
- 网络连接是否正常

### Q: 快捷键不生效？
A: 确保没有与其他应用冲突，可以自定义快捷键。

## 下一步

- 添加图片翻译功能
- 支持更多语言对
- 添加历史记录功能
- 支持自定义Prompt模板

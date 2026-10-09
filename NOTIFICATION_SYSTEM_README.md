# 通知工作台系统

一个自动收集、总结和展示深圳理工大学教务系统通知的工具。

## 功能特性

- 📊 **自动收集**：每周自动从教务系统收集新发布的通知
- 📝 **智能总结**：每条通知100-200字自动总结
- 🔥 **优先级排序**：按重要程度自动分类排序
- 💾 **数据管理**：支持导入、导出、备份和恢复
- 🎨 **美观界面**：现代化的暗色主题界面
- ⏰ **定时任务**：每周自动运行，无需手动操作

## 文件结构

```
.
├── notification-collector.py      # Python自动收集脚本
├── notifications.html              # 通知展示页面
├── notification-manager.html       # 数据管理页面
├── notifications.json              # 通知数据文件（自动生成）
└── personal-website/              # 个人网站目录
    ├── notifications.html          # 通知工作台（集成版）
    └── notification-manager.html   # 数据管理（集成版）
```

## 安装和配置

### 1. 环境要求

- Python 3.7+
- Chrome浏览器
- ChromeDriver（会自动安装）

### 2. 安装Python依赖

```bash
pip install selenium webdriver-manager beautifulsoup4
```

### 3. 配置教务系统账号

编辑 `notification-collector.py` 文件，修改以下部分：

```python
# 在 main() 函数中修改
USERNAME = input("请输入学号/账号：")
PASSWORD = input("请输入密码：")
```

或者直接修改脚本中的硬编码值（不推荐）：

```python
USERNAME = "你的学号"
PASSWORD = "你的密码"
```

### 4. 测试收集功能

```bash
python notification-collector.py
```

输入账号密码后，脚本会自动：
1. 登录教务系统
2. 收集通知
3. 生成总结
4. 按重要程度排序
5. 保存到 notifications.json

## 使用方法

### 方式一：手动收集

1. 运行脚本：`python notification-collector.py`
2. 输入账号密码
3. 等待收集完成
4. 在浏览器中打开 `notifications.html` 查看通知

### 方式二：通过网页界面

1. 在浏览器中打开 `personal-website/notifications.html`
2. 点击"📥 收集通知"按钮
3. 系统会自动读取 `notifications.json` 文件
4. 更新通知列表

### 方式三：自动收集（定时任务）

定时任务已配置为每周一早上9点自动运行。

## 网页功能

### 通知展示页面 (notifications.html)

- **搜索**：按标题或内容搜索通知
- **筛选**：按重要程度筛选（高/中/低）
- **排序**：按时间或重要程度排序
- **添加/编辑/删除**：手动管理通知
- **查看详情**：点击查看完整通知内容
- **收集通知**：一键从JSON文件加载最新通知

### 数据管理页面 (notification-manager.html)

- **导出数据**：将通知导出为JSON文件
- **导入数据**：从JSON文件导入通知
- **备份数据**：创建备份文件
- **恢复数据**：从备份恢复数据
- **清空数据**：删除所有通知
- **操作日志**：查看所有操作记录
- **数据预览**：预览通知列表

## 重要程度分类

- 🔴 **高优先级**：紧急通知、重要公告
- 🟡 **中优先级**：常规通知、一般公告
- 🟢 **低优先级**：通知、一般信息

## 数据存储

- **本地存储**：使用localStorage存储通知
- **文件存储**：notifications.json存储完整数据
- **备份**：支持定期备份功能

## 定时任务配置

定时任务配置：
- **频率**：每周一早上9点
- **Cron表达式**：`0 9 * * 1`
- **执行内容**：运行Python脚本收集通知

如需修改定时任务：
1. 访问 ZCode 定时任务管理页面
2. 找到"每周收集通知"任务
3. 编辑cron表达式或执行内容

## 故障排除

### 问题1：无法登录教务系统

**原因**：账号密码错误或页面结构变化

**解决方案**：
1. 检查账号密码
2. 打开浏览器手动登录，查看实际页面结构
3. 修改 `notification-collector.py` 中的登录逻辑

### 问题2：无法收集到通知

**原因**：页面结构变化或选择器错误

**解决方案**：
1. 使用浏览器开发者工具检查页面元素
2. 更新 `parse_notifications()` 函数中的选择器
3. 查看脚本输出的错误信息

### 问题3：Python脚本无法运行

**原因**：依赖包未安装或版本不兼容

**解决方案**：
```bash
# 重新安装依赖
pip install --upgrade selenium webdriver-manager beautifulsoup4
```

### 问题4：定时任务未执行

**原因**：任务未启用或cron表达式错误

**解决方案**：
1. 检查任务状态是否为"active"
2. 查看Cron表达式是否正确
3. 查看执行日志

## 定制化修改

### 修改通知总结长度

编辑 `notification-collector.py` 中的 `summarize_notification()` 函数：

```python
def summarize_notification(self, title, content):
    # 修改100-200字的范围
    summary = f"{title}。{content[:150]}..."  # 改为150字
    # ...
```

### 修改重要程度判断规则

编辑 `parse_notifications()` 函数：

```python
# 添加更多关键词判断
if '考试' in title_text or '成绩' in title_text:
    importance = 'high'
elif '通知' in title_text:
    importance = 'low'
```

### 修改界面主题颜色

编辑CSS文件中的 `:root` 变量：

```css
:root {
  --accent-blue: #3b82f6;      /* 主色调 */
  --accent-purple: #8b5cf6;    /* 辅助色 */
  --accent-green: #10b981;     /* 成功色 */
  --accent-yellow: #f59e0b;    /* 警告色 */
  --accent-red: #ef4444;       /* 错误色 */
}
```

## 安全建议

1. **不要在代码中硬编码密码**：使用环境变量或配置文件
2. **定期备份数据**：防止数据丢失
3. **保护notifications.json**：不要分享给他人
4. **使用强密码**：教务系统密码

## 技术支持

如遇问题，请检查：
1. Python版本和依赖包版本
2. Chrome浏览器版本
3. 教务系统页面结构
4. 定时任务执行日志

## 更新日志

### v1.0.0 (2026-10-09)
- 初始版本发布
- 支持自动收集通知
- 支持智能总结
- 支持优先级排序
- 支持数据管理
- 配置定时任务

## 许可证

MIT License

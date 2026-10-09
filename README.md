# 课程提醒工作台

一个极简风格的本地课程提醒网页应用，用于查看和管理课程信息，并在课程开始前12小时自动提醒。

## 功能特点

- 🎨 **极简设计**：黑黄色配色方案，低饱和度，视觉舒适
- ⏰ **智能提醒**：课程开始前12小时自动弹出倒计时通知
- 📅 **课程管理**：显示课程时间、地点、科目和老师信息
- 🔄 **自动刷新**：每分钟自动检查课程状态
- 💾 **本地存储**：使用浏览器本地存储保存数据
- 📱 **响应式设计**：支持桌面和移动设备

## 使用方法

### 1. 打开应用

双击打开 `course-workbench.html` 文件，或者使用浏览器打开该文件。

### 2. 登录

**方式一：手动登录**
- 输入学号和密码
- 点击"登录"按钮

**方式二：使用演示数据**
- 点击"使用演示数据"按钮
- 可以立即查看课程效果

### 3. 查看课程

登录成功后，页面会显示当天的课程列表，包括：
- 课程时间
- 上课地点
- 科目名称
- 授课老师

### 4. 倒计时提醒

当课程开始前12小时，会自动弹出倒计时弹窗：
- 显示距离上课的剩余时间
- 显示课程详细信息
- 可以关闭弹窗

## 如何连接到真实教务系统

### 方法一：直接爬取（推荐）

教务系统的课程信息通常在以下页面：
- 课程表页面：`https://jwxt.sztu.edu.cn/jsxsd/xskb/xskbList.do`
- 个人课表页面：`https://jwxt.sztu.edu.cn/jsxsd/xskb/xskb_view.do`

**需要修改的代码部分：**

在 `course-workbench.html` 文件中，找到 `simulateLogin` 函数，替换为实际的登录请求：

```javascript
async function simulateLogin(username, password) {
    return new Promise((resolve, reject) => {
        // 发送登录请求
        fetch('https://jwxt.sztu.edu.cn/jsxsd/framework/xsMain.htmlx', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `username=${username}&password=${password}`,
            credentials: 'include'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('登录失败');
            }
            return response.text();
        })
        .then(html => {
            // 解析课程信息
            const courses = parseCoursesFromHTML(html);
            currentCourses = courses;
            localStorage.setItem('courses', JSON.stringify(courses));
            resolve(courses);
        })
        .catch(error => {
            reject(error);
        });
    });
}
```

### 方法二：使用教务系统API

教务系统通常提供API接口，可以直接获取课程数据：

```javascript
async function fetchCoursesFromSystem() {
    loading.classList.add('active');

    try {
        // 获取认证Cookie
        const cookie = await loginToSystem();

        // 获取课程列表
        const response = await fetch('https://jwxt.sztu.edu.cn/jsxsd/xskb/xskbList.do', {
            method: 'GET',
            headers: {
                'Cookie': cookie
            }
        });

        const html = await response.text();
        const courses = parseCoursesFromHTML(html);

        currentCourses = courses;
        localStorage.setItem('courses', JSON.stringify(courses));
        renderCourses();

        loading.classList.remove('active');
    } catch (error) {
        console.error('获取课程失败:', error);
        showToast('获取课程失败，请使用演示数据', 'error');
        loading.classList.remove('active');
    }
}
```

### HTML解析函数示例

```javascript
function parseCoursesFromHTML(html) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');

    const courses = [];
    const courseElements = doc.querySelectorAll('.course-item'); // 根据实际页面结构调整选择器

    courseElements.forEach(element => {
        const time = element.querySelector('.time')?.textContent || '';
        const location = element.querySelector('.location')?.textContent || '';
        const subject = element.querySelector('.subject')?.textContent || '';
        const teacher = element.querySelector('.teacher')?.textContent || '';

        if (time && subject) {
            courses.push({
                id: Date.now() + Math.random(),
                time,
                location,
                subject,
                teacher,
                status: 'upcoming'
            });
        }
    });

    return courses;
}
```

## 数据存储

应用使用浏览器的 `localStorage` 存储以下数据：
- 登录状态
- 课程信息
- 通知记录

清除浏览器缓存会清除所有数据。

## 浏览器通知

应用支持桌面通知功能：

1. 第一次使用时，浏览器会询问是否允许通知
2. 点击"允许"后，即使浏览器最小化也会收到通知

## 自定义配置

### 修改提醒时间

在 `startNotificationCheck` 函数中，修改720（分钟）为其他值：

```javascript
// 12小时 = 12 * 60 = 720分钟
// 6小时 = 6 * 60 = 360分钟
// 24小时 = 24 * 60 = 1440分钟
if (startTime - currentMinutes <= 720 && startTime - currentMinutes > 0) {
```

### 修改配色方案

在 `<style>` 标签的 `:root` 部分修改CSS变量：

```css
:root {
    --accent-yellow: #f4d03f;      /* 主黄色 */
    --accent-yellow-dark: #d4ac0d; /* 深黄色 */
    --bg-primary: #1a1a1a;         /* 主背景 */
    --bg-secondary: #2a2a2a;       /* 次级背景 */
    /* ... 其他颜色 */
}
```

## 常见问题

### Q: 为什么无法登录教务系统？

A: 可能的原因：
1. 网络问题，无法访问教务系统
2. 教务系统需要验证码，当前版本未实现
3. 教务系统使用HTTPS证书问题
4. 需要额外的认证步骤

建议使用演示数据查看效果，然后根据实际情况调整代码。

### Q: 如何获取课程数据？

A:
1. 使用浏览器开发者工具查看教务系统页面的HTML结构
2. 找到课程数据的选择器
3. 修改 `parseCoursesFromHTML` 函数中的选择器

### Q: 数据会同步到服务器吗？

A: 不会。所有数据都存储在本地浏览器中，不会上传到任何服务器。

### Q: 可以同时使用多个账号吗？

A: 可以。每次登录都会覆盖之前的数据。建议为不同账号创建不同的浏览器配置文件。

## 技术栈

- HTML5
- CSS3
- JavaScript (ES6+)
- LocalStorage API
- Fetch API

## 许可证

MIT License

## 更新日志

### v1.0.0 (2026-10-09)
- 初始版本
- 基础课程提醒功能
- 极简黑黄色设计
- 12小时倒计时提醒

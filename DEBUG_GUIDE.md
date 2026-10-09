# 课程提醒工作台 - 调试指南

## 快速测试

### 1. 使用演示数据测试

直接双击打开 `course-workbench.html`，点击"使用演示数据"按钮即可查看效果。

### 2. 测试倒计时功能

1. 打开页面，点击"使用演示数据"
2. 在浏览器控制台中执行以下代码，将第一节课的时间改为5分钟后：

```javascript
// 找到第一节课并修改时间
const courses = JSON.parse(localStorage.getItem('courses'));
if (courses.length > 0) {
    const now = new Date();
    const fiveMinutesLater = new Date(now.getTime() + 5 * 60 * 1000);
    courses[0].time = `${String(fiveMinutesLater.getHours()).padStart(2, '0')}:${String(fiveMinutesLater.getMinutes()).padStart(2, '0')} - ${String(fiveMinutesLater.getHours() + 1).padStart(2, '0')}:${String(fiveMinutesLater.getMinutes()).padStart(2, '0')}`;
    localStorage.setItem('courses', JSON.stringify(courses));
    location.reload();
}
```

3. 等待5分钟后，应该会弹出倒计时通知。

## 浏览器控制台调试

### 查看课程数据

```javascript
// 查看当前课程
console.log(JSON.parse(localStorage.getItem('courses')));

// 查看登录状态
console.log(localStorage.getItem('isLoggedIn'));

// 查看通知记录
const today = new Date().toDateString();
console.log(`通知记录: ${localStorage.getItem(`notified-1-${today}`)}`);
```

### 手动触发通知

```javascript
// 手动触发第一节课的通知
const courses = JSON.parse(localStorage.getItem('courses'));
if (courses.length > 0) {
    // 清除通知记录，以便重新触发
    const today = new Date().toDateString();
    localStorage.removeItem(`notified-${courses[0].id}-${today}`);

    // 手动检查通知
    // 需要在页面中添加一个按钮来调用此函数
    // 或者直接在控制台执行：
    showCountdownModal(courses[0], 60); // 60分钟
}
```

### 修改提醒时间

```javascript
// 将提醒时间改为6小时
const courses = JSON.parse(localStorage.getItem('courses'));
courses.forEach(course => {
    course.reminderHours = 6; // 修改提醒时间（小时）
});
localStorage.setItem('courses', JSON.stringify(courses));
location.reload();
```

## 网络请求调试

### 检查登录请求

在浏览器开发者工具的Network标签中：

1. 打开 `course-workbench.html`
2. 输入账号密码并点击登录
3. 查看Network标签中的请求
4. 找到登录相关的请求，查看请求头和响应

### 模拟教务系统响应

在浏览器控制台中，可以模拟教务系统的响应：

```javascript
// 模拟登录成功
const mockHtml = `
<div class="course-list">
    <div class="course-item">
        <div class="time">08:00 - 09:35</div>
        <div class="location">教学楼 A101</div>
        <div class="subject">高等数学</div>
        <div class="teacher">张教授</div>
    </div>
    <div class="course-item">
        <div class="time">10:00 - 11:35</div>
        <div class="location">教学楼 B202</div>
        <div class="subject">大学英语</div>
        <div class="teacher">李老师</div>
    </div>
</div>
`;

// 模拟解析函数
function parseCoursesFromHTML(html) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');

    const courses = [];
    const courseElements = doc.querySelectorAll('.course-item');

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

// 测试解析
const courses = parseCoursesFromHTML(mockHtml);
console.log('解析的课程:', courses);
localStorage.setItem('courses', JSON.stringify(courses));
```

## 常见问题排查

### 问题1：倒计时不弹出

**可能原因：**
1. 课程状态不是 'upcoming'
2. 通知记录已存在
3. JavaScript错误

**解决方法：**
```javascript
// 检查课程状态
const courses = JSON.parse(localStorage.getItem('courses'));
console.log('课程状态:', courses.map(c => ({
    subject: c.subject,
    status: c.status,
    time: c.time
})));

// 查看通知记录
const today = new Date().toDateString();
courses.forEach(course => {
    const notified = localStorage.getItem(`notified-${course.id}-${today}`);
    console.log(`${course.subject}: ${notified ? '已通知' : '未通知'}`);
});

// 清除通知记录以便测试
courses.forEach(course => {
    localStorage.removeItem(`notified-${course.id}-${today}`);
});
```

### 问题2：课程不显示

**可能原因：**
1. localStorage中没有课程数据
2. 数据格式不正确

**解决方法：**
```javascript
// 检查数据
console.log('课程数据:', localStorage.getItem('courses'));

// 清空并重新加载
localStorage.removeItem('courses');
location.reload();

// 或者直接使用演示数据
localStorage.setItem('courses', JSON.stringify([
    {
        id: 1,
        time: '08:00 - 09:35',
        location: '教学楼 A101',
        subject: '高等数学',
        teacher: '张教授',
        status: 'upcoming'
    }
]));
location.reload();
```

### 问题3：样式不正确

**可能原因：**
1. CSS文件路径错误
2. 浏览器缓存问题
3. CSS选择器不匹配

**解决方法：**
1. 强制刷新页面（Ctrl + F5 或 Cmd + Shift + R）
2. 清除浏览器缓存
3. 检查浏览器控制台是否有CSS错误

## 性能优化建议

### 减少DOM操作

```javascript
// 不好的做法：每次都重新创建整个HTML
scheduleGrid.innerHTML = courses.map(...).join('');

// 好的做法：只更新需要变化的元素
courses.forEach(course => {
    const card = document.querySelector(`.schedule-card[data-id="${course.id}"]`);
    if (card) {
        card.querySelector('.schedule-time-text').textContent = course.time;
        // ... 更新其他元素
    }
});
```

### 使用事件委托

```javascript
// 不好的做法：为每个按钮添加事件监听
document.querySelectorAll('.schedule-card').forEach(card => {
    card.addEventListener('click', handleCardClick);
});

// 好的做法：使用事件委托
scheduleGrid.addEventListener('click', (e) => {
    const card = e.target.closest('.schedule-card');
    if (card) {
        handleCardClick(card);
    }
});
```

## 浏览器兼容性

### Chrome/Edge（推荐）
- ✅ 完全支持
- ✅ 性能最佳

### Firefox
- ✅ 完全支持
- ⚠️ 需要启用JavaScript

### Safari
- ✅ 完全支持
- ⚠️ 需要启用JavaScript

### IE11
- ❌ 不支持（需要降级处理）

## 日志记录

可以在代码中添加日志记录功能：

```javascript
// 创建日志工具
const logger = {
    log: (...args) => console.log('[课程提醒]', ...args),
    error: (...args) => console.error('[课程提醒错误]', ...args),
    warn: (...args) => console.warn('[课程提醒警告]', ...args)
};

// 使用
logger.log('课程加载完成', courses);
logger.error('登录失败', error);
```

## 下一步

1. ✅ 测试演示数据功能
2. ✅ 测试倒计时通知
3. ✅ 检查浏览器控制台是否有错误
4. 🔜 连接真实教务系统
5. 🔜 自定义课程数据格式
6. 🔜 添加更多功能（如课程详情、历史记录等）

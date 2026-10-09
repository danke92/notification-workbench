@echo off
chcp 65001 >nul
echo ========================================
echo   课程提醒工作台 v1.1.1
echo ========================================
echo.
echo 新功能：
echo   ✨ 学期课表视图 - 查看整个学期的课程安排
echo   ✨ 周次范围显示 - 标注每节课的周次信息
echo   ✨ 课程详情弹窗 - 点击查看完整课程信息
echo   🔧 已修复课表显示问题
echo.
echo 正在启动课程提醒工作台...
echo.
echo 请使用 Chrome、Edge 或 Firefox 浏览器打开
echo.
echo 如果浏览器没有自动打开，请手动打开以下文件：
echo   course-workbench.html
echo.
echo 按任意键打开浏览器...
pause >nul

start "" "course-workbench.html"

echo.
echo 已启动课程提醒工作台！
echo.
echo 提示：
echo   - 使用演示数据：点击"使用演示数据"按钮
echo   - 手动登录：输入学号和密码
echo   - 查看学期课表：点击"学期课表"标签
echo   - 查看课程详情：点击任意课程卡片
echo   - 如果课表不显示：请按 Ctrl + F5 强制刷新
echo.
echo 详细说明请查看：
echo   - 功能快速参考.md
echo   - 学期课表功能说明.md
echo   - 修复说明.md
echo.
pause

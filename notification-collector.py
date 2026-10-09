#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通知收集器 - 自动登录深圳理工大学教务系统并收集通知
每周自动运行，收集新发布的通知并生成总结
"""

import json
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup


class NotificationCollector:
    def __init__(self):
        self.driver = None
        self.notifications = []

    def setup_driver(self):
        """配置Chrome浏览器驱动"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # 无头模式
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')

        # 使用webdriver_manager自动下载驱动
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

    def login(self, username, password):
        """登录教务系统"""
        try:
            print("正在打开教务系统登录页面...")
            self.driver.get('https://nbw.sztu.edu.cn/')

            # 等待登录表单加载
            wait = WebDriverWait(self.driver, 10)

            # 填写用户名（可能需要根据实际页面调整选择器）
            try:
                username_input = wait.until(
                    EC.presence_of_element_located((By.NAME, 'username'))
                )
                username_input.send_keys(username)
            except:
                print("警告：未找到用户名输入框，尝试其他选择器")
                try:
                    username_input = self.driver.find_element(By.ID, 'username')
                    username_input.send_keys(username)
                except Exception as e:
                    print(f"登录失败：{e}")
                    return False

            # 填写密码
            try:
                password_input = self.driver.find_element(By.NAME, 'password')
                password_input.send_keys(password)
            except:
                try:
                    password_input = self.driver.find_element(By.ID, 'password')
                    password_input.send_keys(password)
                except Exception as e:
                    print(f"登录失败：{e}")
                    return False

            # 点击登录按钮
            try:
                login_button = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
                login_button.click()
            except:
                try:
                    login_button = self.driver.find_element(By.XPATH, '//button[contains(text(), "登录")]')
                    login_button.click()
                except Exception as e:
                    print(f"登录失败：{e}")
                    return False

            # 等待登录完成
            time.sleep(3)
            print("登录成功！")
            return True

        except Exception as e:
            print(f"登录过程出错：{e}")
            return False

    def collect_notifications(self):
        """收集通知"""
        try:
            print("正在访问通知页面...")

            # 等待页面加载
            time.sleep(2)

            # 获取页面内容
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')

            # 解析通知（需要根据实际页面结构调整）
            notifications = self.parse_notifications(soup)

            if notifications:
                print(f"成功收集 {len(notifications)} 条通知")
                self.notifications = notifications
                return True
            else:
                print("未找到通知，请检查页面结构")
                return False

        except Exception as e:
            print(f"收集通知出错：{e}")
            return False

    def parse_notifications(self, soup):
        """解析通知内容（需要根据实际页面结构调整）"""
        notifications = []

        # 这里需要根据实际的教务系统页面结构调整选择器
        # 示例：假设通知在某个特定的class或id下
        try:
            # 示例：查找所有通知项
            notification_items = soup.find_all('div', class_='notification-item')

            for item in notification_items:
                title = item.find('h3') or item.find('a', class_='title')
                if title:
                    title_text = title.get_text(strip=True)
                else:
                    continue

                content = item.find('div', class_='content') or item.find('p')
                if content:
                    content_text = content.get_text(strip=True)
                else:
                    continue

                date = item.find('time') or item.find('span', class_='date')
                if date:
                    date_text = date.get_text(strip=True)
                else:
                    date_text = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # 简单判断重要程度（可以根据实际需求调整）
                importance = 'medium'
                if '重要' in title_text or '紧急' in title_text:
                    importance = 'high'
                elif '通知' in title_text:
                    importance = 'low'

                # 总结通知（100-200字）
                summary = self.summarize_notification(title_text, content_text)

                notifications.append({
                    'title': title_text,
                    'content': content_text,
                    'summary': summary,
                    'importance': importance,
                    'date': date_text,
                    'collected_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })

        except Exception as e:
            print(f"解析通知时出错：{e}")

        return notifications

    def summarize_notification(self, title, content):
        """总结通知（100-200字）"""
        # 简单的总结策略：取标题和前几句话
        summary = f"{title}。{content[:100]}"

        # 确保长度在100-200字之间
        if len(summary) < 100:
            summary = summary + "。请查看详情了解完整信息。"
        elif len(summary) > 200:
            summary = summary[:200] + "..."

        return summary

    def sort_by_importance(self):
        """按重要程度排序"""
        importance_order = {'high': 3, 'medium': 2, 'low': 1}
        self.notifications.sort(
            key=lambda x: importance_order[x['importance']],
            reverse=True
        )

    def save_to_file(self, filename='notifications.json'):
        """保存到JSON文件"""
        try:
            data = {
                'collected_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'total_count': len(self.notifications),
                'notifications': self.notifications
            }

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"通知已保存到 {filename}")
            return True

        except Exception as e:
            print(f"保存文件失败：{e}")
            return False

    def run(self, username, password):
        """运行收集流程"""
        try:
            print("=" * 50)
            print("通知收集器启动")
            print("=" * 50)

            # 设置驱动
            self.setup_driver()

            # 登录
            if not self.login(username, password):
                print("登录失败，请检查用户名和密码")
                return False

            # 收集通知
            if not self.collect_notifications():
                print("未收集到通知")
                return False

            # 排序
            self.sort_by_importance()

            # 保存
            if self.save_to_file():
                print(f"\n收集完成！共 {len(self.notifications)} 条通知")
                print("\n通知列表：")
                for i, notif in enumerate(self.notifications[:5], 1):
                    print(f"\n{i}. [{self.get_importance_label(notif['importance'])}] {notif['title']}")
                    print(f"   {notif['summary'][:50]}...")
                if len(self.notifications) > 5:
                    print(f"\n... 还有 {len(self.notifications) - 5} 条通知")

                return True
            else:
                return False

        except Exception as e:
            print(f"运行出错：{e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # 关闭浏览器
            if self.driver:
                self.driver.quit()

    def get_importance_label(self, importance):
        """获取重要程度标签"""
        labels = {
            'high': '🔴 高优先级',
            'medium': '🟡 中优先级',
            'low': '🟢 低优先级'
        }
        return labels.get(importance, '⚪ 未知')


def main():
    """主函数"""
    import sys

    # 从命令行参数读取账号密码
    USERNAME = None
    PASSWORD = None

    # 检查命令行参数
    if len(sys.argv) >= 3:
        USERNAME = sys.argv[1]
        PASSWORD = sys.argv[2]
    else:
        # 从环境变量读取
        USERNAME = os.getenv('NBW_USERNAME')
        PASSWORD = os.getenv('NBW_PASSWORD')

        if not USERNAME or not PASSWORD:
            # 交互式输入
            USERNAME = input("请输入学号/账号：")
            PASSWORD = input("请输入密码：")

    if not USERNAME or not PASSWORD:
        print("用户名和密码不能为空")
        print("使用方法：python notification-collector.py <用户名> <密码>")
        print("或设置环境变量：NBW_USERNAME 和 NBW_PASSWORD")
        return

    collector = NotificationCollector()
    success = collector.run(USERNAME, PASSWORD)

    if success:
        print("\n✅ 通知收集成功！")
    else:
        print("\n❌ 通知收集失败")


if __name__ == '__main__':
    main()

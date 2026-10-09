// 挂机脚本：每2分钟滑动一次，持续6小时
const puppeteer = require('puppeteer');
const fs = require('fs');

const URL = 'http://10.1.20.14/redir.php?catalog_id=121';
const SCROLL_INTERVAL = 2 * 60 * 1000; // 2分钟（毫秒）
const DURATION = 6 * 60 * 60 * 1000; // 6小时（毫秒）
const TOTAL_SCROLLS = Math.floor(DURATION / SCROLL_INTERVAL); // 总共需要滚动的次数

// 创建日志文件
const logFile = fs.createWriteStream('auto-scroll.log', { flags: 'a' });
function log(message) {
  const timestamp = new Date().toLocaleString('zh-CN');
  const logMessage = `[${timestamp}] ${message}\n`;
  console.log(logMessage.trim());
  logFile.write(logMessage);
}

(async () => {
  log(`=== 挂机任务开始 ===`);
  log(`目标URL: ${URL}`);
  log(`滚动间隔: ${SCROLL_INTERVAL / 1000 / 60}分钟`);
  log(`持续时间: ${DURATION / 1000 / 60 / 60}小时`);
  log(`总滚动次数: ${TOTAL_SCROLLS}`);

  const browser = await puppeteer.launch({
    headless: false, // 显示浏览器窗口
    defaultViewport: null,
    args: ['--start-maximized', '--disable-notifications']
  });

  const page = await browser.newPage();

  // 设置较长的超时时间
  page.setDefaultTimeout(60000);

  try {
    log('正在访问网站...');
    await page.goto(URL, {
      waitUntil: 'networkidle2',
      timeout: 60000
    });
    log('页面加载完成');

    // 等待页面完全加载
    await new Promise(resolve => setTimeout(resolve, 3000));
    log('等待页面稳定...');

    // 获取初始页面高度
    let previousHeight = await page.evaluate(() => document.body.scrollHeight);
    log(`初始页面高度: ${previousHeight}px`);

    // 记录开始时间
    const startTime = Date.now();
    const endTime = startTime + DURATION;

    // 开始滚动循环
    for (let i = 1; i <= TOTAL_SCROLLS; i++) {
      const currentTime = Date.now();
      const timeRemaining = endTime - currentTime;
      const minutesRemaining = Math.floor(timeRemaining / 1000 / 60);

      log(`\n[${i}/${TOTAL_SCROLLS}] 正在滚动页面... (剩余时间: ${minutesRemaining}分钟)`);

      // 滚动到页面底部
      await page.evaluate(() => {
        window.scrollTo({
          top: document.body.scrollHeight,
          behavior: 'smooth'
        });
      });

      // 等待滚动完成
      await new Promise(resolve => setTimeout(resolve, 2000));

      // 获取当前页面高度
      const currentHeight = await page.evaluate(() => document.body.scrollHeight);
      const scrollHeight = currentHeight - previousHeight;

      log(`  当前页面高度: ${currentHeight}px`);
      log(`  本次滚动高度: ${scrollHeight}px`);

      // 更新之前的高度
      previousHeight = currentHeight;

      // 如果还有剩余时间，等待2分钟
      if (currentTime < endTime) {
        const sleepTime = Math.min(SCROLL_INTERVAL, timeRemaining);
        log(`  等待 ${sleepTime / 1000 / 60} 分钟后进行下一次滚动...`);
        await new Promise(resolve => setTimeout(resolve, sleepTime));
      }
    }

    log(`\n=== 挂机任务完成 ===`);
    log(`总耗时: ${((Date.now() - startTime) / 1000 / 60).toFixed(2)}分钟`);
    log(`总滚动次数: ${TOTAL_SCROLLS}`);
    log(`平均每分钟滚动: ${(TOTAL_SCROLLS / ((Date.now() - startTime) / 1000 / 60)).toFixed(2)}次`);

  } catch (error) {
    log(`\n错误: ${error.message}`);
    console.error(error);
  } finally {
    // 等待5秒后关闭浏览器
    log('等待5秒后关闭浏览器...');
    await new Promise(resolve => setTimeout(resolve, 5000));
    await browser.close();
    logFile.end();
  }
})();

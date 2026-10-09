// 使用 Puppeteer 访问网站并检测登录表单
const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({
    headless: false,
    defaultViewport: null,
    args: ['--start-maximized']
  });

  const page = await browser.newPage();

  // 设置较长的超时时间
  page.setDefaultTimeout(60000);

  // 访问网站
  console.log('正在访问网站...');
  try {
    await page.goto('http://10.1.20.14/redir.php?catalog_id=121', {
      waitUntil: 'networkidle2',
      timeout: 60000
    });
    console.log('页面加载完成');

    // 截图
    await page.screenshot({ path: 'homepage.png' });
    console.log('首页截图已保存: homepage.png');

    // 获取页面标题
    const title = await page.title();
    console.log('页面标题:', title);

    // 获取页面文本内容（前500个字符）
    const bodyText = await page.evaluate(() => document.body.innerText.substring(0, 500));
    console.log('页面内容预览:', bodyText);

    // 检查是否有登录表单
    const hasLoginInput = await page.evaluate(() => {
      const inputs = document.querySelectorAll('input');
      const buttons = document.querySelectorAll('button, input[type="submit"]');

      let usernameInput = null;
      let passwordInput = null;
      let submitButton = null;

      for (const input of inputs) {
        const name = input.name.toLowerCase();
        const id = input.id.toLowerCase();
        const type = input.type.toLowerCase();

        if (type === 'text' && !usernameInput) {
          usernameInput = input;
        }
        if (type === 'password' && !passwordInput) {
          passwordInput = input;
        }
      }

      for (const btn of buttons) {
        const text = btn.innerText.toLowerCase();
        if (text.includes('登录') || text.includes('login') || text.includes('提交') || text.includes('submit')) {
          if (!submitButton) {
            submitButton = btn;
          }
        }
      }

      return {
        usernameInput: !!usernameInput,
        passwordInput: !!passwordInput,
        submitButton: !!submitButton,
        loginForm: document.querySelector('form') !== null
      };
    });
    console.log('登录表单检测:', hasLoginInput);

    // 等待10秒，让用户可以看到页面
    await new Promise(resolve => setTimeout(resolve, 10000));

    await browser.close();
    console.log('测试完成');

  } catch (error) {
    console.error('访问网站失败:', error.message);
    await browser.close();
    throw error;
  }
})();

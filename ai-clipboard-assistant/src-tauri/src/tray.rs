use tauri::{Manager, AppHandle};
use std::sync::Arc;
use std::sync::atomic::AtomicBool;
use anyhow::Result;
use tauri::tray::{TrayIcon, TrayIconBuilder, TrayIconId};

pub struct Tray {
    app_handle: AppHandle,
    _stop_event: Arc<AtomicBool>,
}

impl Tray {
    pub fn new(app: &AppHandle) -> Result<Self> {
        let stop_event = Arc::new(AtomicBool::new(false));
        
        let tray = Tray {
            app_handle: app.clone(),
            _stop_event: stop_event.clone(),
        };
        
        // 创建系统托盘
        tray.create_tray_icon()?;
        
        // 显示启动通知
        tray.show_notification("AI剪贴板助手", "已启动，右键托盘图标可查看菜单")?;
        
        // 启动后台线程
        std::thread::spawn(move || {
            while !stop_event.load(std::sync::atomic::Ordering::Relaxed) {
                std::thread::sleep(std::time::Duration::from_secs(1));
            }
        });
        
        Ok(tray)
    }
    
    fn create_tray_icon(&self) -> Result<()> {
        let icon = self.app_handle
            .tray_by_id("main")
            .ok_or_else(|| anyhow::anyhow!("托盘图标不存在"))?;
        
        // 添加右键菜单
        let menu = tauri::menu::Menu::new()
            .add_item(tauri::menu::MenuItem::new(
                "显示设置",
                true,
                Some("settings"),
                None,
                None,
            ))
            .add_native_item(tauri::menu::NativeMenuItem::Separator)
            .add_item(tauri::menu::MenuItem::new(
                "复制翻译结果",
                true,
                Some("copy-translate"),
                None,
                None,
            ))
            .add_item(tauri::menu::MenuItem::new(
                "复制总结结果",
                true,
                Some("copy-summarize"),
                None,
                None,
            ))
            .add_native_item(tauri::menu::NativeMenuItem::Separator)
            .add_item(tauri::menu::MenuItem::new(
                "退出程序",
                true,
                Some("quit"),
                None,
                None,
            ));
        
        icon.set_menu(Some(menu))?;
        
        Ok(())
    }
    
    pub fn show_notification(&self, title: &str, body: &str) -> Result<()> {
        use tauri::Notification;
        
        Notification::new("AI剪贴板助手")
            .title(title)
            .body(body)
            .show()?;
        
        Ok(())
    }
    
    pub fn setup_hotkeys(&self) -> Result<()> {
        // 这里需要调用Tauri的全局热键API
        // 暂时留空
        Ok(())
    }
    
    pub fn stop(&self) {
        self._stop_event.store(true, std::sync::atomic::Ordering::Relaxed);
    }
}

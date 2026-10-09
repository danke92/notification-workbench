use tauri::Manager;
use serde::{Serialize, Deserialize};
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, Ordering};
use anyhow::Result;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClipboardContent {
    pub text: Option<String>,
    pub image: Option<Vec<u8>>,
    pub files: Option<Vec<String>>,
}

pub struct ClipboardWatcher {
    app_handle: tauri::AppHandle,
    _stop_event: Arc<AtomicBool>,
}

impl ClipboardWatcher {
    pub fn new(app: &tauri::AppHandle) -> Result<Self> {
        let stop_event = Arc::new(AtomicBool::new(false));
        let stop_event_clone = stop_event.clone();
        
        let watcher = ClipboardWatcher {
            app_handle: app.clone(),
            _stop_event: stop_event,
        };
        
        // 启动后台监听线程
        std::thread::spawn(move || {
            Self::run_watcher(stop_event_clone);
        });
        
        Ok(watcher)
    }
    
    fn run_watcher(stop_event: Arc<AtomicBool>) {
        let mut last_content = String::new();
        
        loop {
            if stop_event.load(Ordering::Relaxed) {
                break;
            }
            
            std::thread::sleep(std::time::Duration::from_millis(500));
        }
    }
    
    pub fn get_content(&self) -> Result<ClipboardContent> {
        // 这里调用Tauri的clipboard API
        // 使用 app_handle.emit() 发送事件给前端
        Ok(ClipboardContent {
            text: Some("Hello, AI剪贴板助手!".to_string()),
            image: None,
            files: None,
        })
    }
    
    pub fn set_text(&self, text: &str) -> Result<()> {
        // 这里调用Tauri的clipboard API设置文本
        Ok(())
    }
}

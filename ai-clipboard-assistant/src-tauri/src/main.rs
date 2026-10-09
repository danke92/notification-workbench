use tauri::Manager;
use std::sync::Mutex;
use anyhow::Result;

mod clipboard;
mod llm;
mod tray;
mod commands;
mod config;

fn main() -> Result<()> {
    tauri::Builder::default()
        .setup(|app| {
            // 初始化系统托盘
            tray::Tray::new(app)?;
            
            // 初始化剪贴板监听
            clipboard::ClipboardWatcher::new(app)?;
            
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::translate_text,
            commands::summarize_text,
            commands::get_config,
            commands::save_config,
            commands::copy_to_clipboard,
        ])
        .run(tauri::generate_context!())?;
    
    Ok(())
}

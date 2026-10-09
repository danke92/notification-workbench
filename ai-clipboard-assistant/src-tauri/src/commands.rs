use tauri::State;
use crate::config::Config;
use crate::llm::LLMClient;
use crate::clipboard::ClipboardWatcher;
use anyhow::Result;

#[tauri::command]
pub async fn translate_text(
    text: String,
    config: State<'_, Config>,
) -> Result<String, String> {
    let client = LLMClient::new(config.llm.clone());
    let request = crate::llm::TranslateRequest {
        text,
        source_lang: "Chinese".to_string(),
        target_lang: "English".to_string(),
    };
    
    let response = client.translate(request).await.map_err(|e| {
        e.to_string()
    })?;
    
    Ok(response.content)
}

#[tauri::command]
pub async fn summarize_text(
    text: String,
    config: State<'_, Config>,
) -> Result<String, String> {
    let client = LLMClient::new(config.llm.clone());
    let request = crate::llm::SummarizeRequest {
        text,
        max_length: Some(200),
    };
    
    let response = client.summarize(request).await.map_err(|e| {
        e.to_string()
    })?;
    
    Ok(response.content)
}

#[tauri::command]
pub fn get_config(config: State<'_, Config>) -> Config {
    config.clone()
}

#[tauri::command]
pub fn save_config(
    config: State<'_, Config>,
    new_config: Config,
) -> Result<(), String> {
    new_config.save().map_err(|e| {
        e.to_string()
    })?;
    Ok(())
}

#[tauri::command]
pub fn copy_to_clipboard(text: String) -> Result<(), String> {
    // 这里调用Tauri的clipboard API
    // 使用 webview窗口的JavaScript API
    Ok(())
}

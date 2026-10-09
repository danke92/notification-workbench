use serde::{Deserialize, Serialize};
use anyhow::Result;
use reqwest::Client;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LLMConfig {
    pub provider: String,
    pub api_key: String,
    pub base_url: String,
    pub model: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TranslateRequest {
    pub text: String,
    pub source_lang: String,
    pub target_lang: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SummarizeRequest {
    pub text: String,
    pub max_length: Option<usize>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LLMResponse {
    pub content: String,
    pub model: String,
}

pub struct LLMClient {
    config: LLMConfig,
    client: Client,
}

impl LLMClient {
    pub fn new(config: LLMConfig) -> Self {
        LLMClient {
            config,
            client: Client::new(),
        }
    }
    
    pub async fn translate(&self, request: TranslateRequest) -> Result<LLMResponse> {
        let prompt = format!(
            "请将以下{}文本翻译成{}:\n\n{}",
            request.source_lang, request.target_lang, request.text
        );
        
        self.call_llm(prompt).await
    }
    
    pub async fn summarize(&self, request: SummarizeRequest) -> Result<LLMResponse> {
        let prompt = format!(
            "请总结以下文本，保持核心意思:\n\n{}",
            request.text
        );
        
        self.call_llm(prompt).await
    }
    
    async fn call_llm(&self, prompt: String) -> Result<LLMResponse> {
        let url = format!("{}/chat/completions", self.config.base_url);
        
        let body = serde_json::json!({
            "model": self.config.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        });
        
        let response = self.client
            .post(&url)
            .header("Authorization", format!("Bearer {}", self.config.api_key))
            .header("Content-Type", "application/json")
            .json(&body)
            .send()
            .await?;
        
        if !response.status().is_success() {
            let error_text = response.text().await?;
            return Err(anyhow::anyhow!("LLM API调用失败: {}", error_text));
        }
        
        let json: serde_json::Value = response.json().await?;
        
        let content = json["choices"][0]["message"]["content"]
            .as_str()
            .unwrap_or("")
            .to_string();
        
        Ok(LLMResponse {
            content,
            model: self.config.model.clone(),
        })
    }
    
    pub fn set_config(&mut self, config: LLMConfig) {
        self.config = config;
    }
}

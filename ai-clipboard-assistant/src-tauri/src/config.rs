use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Config {
    pub llm: LLMConfig,
    pub hotkeys: HotkeysConfig,
    pub features: FeaturesConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LLMConfig {
    pub provider: String,
    pub api_key: String,
    pub base_url: String,
    pub model: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HotkeysConfig {
    pub translate: String,
    pub summarize: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FeaturesConfig {
    pub auto_translate: bool,
    pub auto_summarize: bool,
    pub show_popup: bool,
}

impl Default for Config {
    fn default() -> Self {
        Self {
            llm: LLMConfig {
                provider: "openai".to_string(),
                api_key: "".to_string(),
                base_url: "https://api.openai.com/v1".to_string(),
                model: "gpt-3.5-turbo".to_string(),
            },
            hotkeys: HotkeysConfig {
                translate: "Ctrl+Shift+V".to_string(),
                summarize: "Ctrl+Shift+S".to_string(),
            },
            features: FeaturesConfig {
                auto_translate: true,
                auto_summarize: false,
                show_popup: true,
            },
        }
    }
}

impl Config {
    pub fn load() -> Result<Self> {
        let home_dir = directories::BaseDirs::new()
            .ok_or_else(|| anyhow::anyhow!("无法获取用户主目录"))?;
        
        let config_path = home_dir
            .config_dir()
            .join("ai-clipboard-assistant")
            .join("config.ini");
        
        if config_path.exists() {
            let content = std::fs::read_to_string(&config_path)?;
            let ini = rust_ini::Ini::load_from_str(&content)
                .map_err(|e| anyhow::anyhow!("解析配置文件失败: {}", e))?;
            
            let mut config = Self::default();
            
            if let Some(section) = ini.get("llm") {
                if let Some(provider) = section.get("provider") {
                    config.llm.provider = provider.clone();
                }
                if let Some(api_key) = section.get("api_key") {
                    config.llm.api_key = api_key.clone();
                }
                if let Some(base_url) = section.get("base_url") {
                    config.llm.base_url = base_url.clone();
                }
                if let Some(model) = section.get("model") {
                    config.llm.model = model.clone();
                }
            }
            
            if let Some(section) = ini.get("hotkeys") {
                if let Some(translate) = section.get("translate") {
                    config.hotkeys.translate = translate.clone();
                }
                if let Some(summarize) = section.get("summarize") {
                    config.hotkeys.summarize = summarize.clone();
                }
            }
            
            if let Some(section) = ini.get("features") {
                if let Some(auto_translate) = section.get("auto_translate") {
                    config.features.auto_translate = auto_translate == "true";
                }
                if let Some(auto_summarize) = section.get("auto_summarize") {
                    config.features.auto_summarize = auto_summarize == "true";
                }
                if let Some(show_popup) = section.get("show_popup") {
                    config.features.show_popup = show_popup == "true";
                }
            }
            
            Ok(config)
        } else {
            Ok(Self::default())
        }
    }
    
    pub fn save(&self) -> Result<()> {
        let home_dir = directories::BaseDirs::new()
            .ok_or_else(|| anyhow::anyhow!("无法获取用户主目录"))?;
        
        let config_dir = home_dir
            .config_dir()
            .join("ai-clipboard-assistant");
        
        std::fs::create_dir_all(&config_dir)?;
        
        let config_path = config_dir.join("config.ini");
        
        let mut ini = rust_ini::Ini::new();
        
        let mut llm_section = rust_ini::Properties::new();
        llm_section.insert("provider", self.llm.provider.clone());
        llm_section.insert("api_key", self.llm.api_key.clone());
        llm_section.insert("base_url", self.llm.base_url.clone());
        llm_section.insert("model", self.llm.model.clone());
        ini.insert("llm", llm_section);
        
        let mut hotkeys_section = rust_ini::Properties::new();
        hotkeys_section.insert("translate", self.hotkeys.translate.clone());
        hotkeys_section.insert("summarize", self.hotkeys.summarize.clone());
        ini.insert("hotkeys", hotkeys_section);
        
        let mut features_section = rust_ini::Properties::new();
        features_section.insert("auto_translate", self.features.auto_translate.to_string());
        features_section.insert("auto_summarize", self.features.auto_summarize.to_string());
        features_section.insert("show_popup", self.features.show_popup.to_string());
        ini.insert("features", features_section);
        
        let content = ini.write_to_string()?;
        std::fs::write(&config_path, content)?;
        
        Ok(())
    }
}

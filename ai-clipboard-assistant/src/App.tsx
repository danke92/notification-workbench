import { useState, useEffect } from 'react'
import { invoke } from '@tauri-apps/api/tauri'
import { listen } from '@tauri-apps/api/event'

function App() {
  const [text, setText] = useState('')
  const [translated, setTranslated] = useState('')
  const [summarized, setSummarized] = useState('')
  const [config, setConfig] = useState<any>({})
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    // 加载配置
    invoke('get_config').then(setConfig).catch(console.error)

    // 监听剪贴板变化
    listen('clipboard-changed', (event) => {
      setText(event.payload as string)
    })
  }, [])

  const handleTranslate = async () => {
    if (!text) return
    setLoading(true)
    try {
      const result = await invoke<string>('translate_text', { text })
      setTranslated(result)
    } catch (error) {
      console.error('翻译失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSummarize = async () => {
    if (!text) return
    setLoading(true)
    try {
      const result = await invoke<string>('summarize_text', { text })
      setSummarized(result)
    } catch (error) {
      console.error('总结失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = async (content: string) => {
    try {
      await invoke('copy_to_clipboard', { text: content })
      alert('已复制到剪贴板')
    } catch (error) {
      console.error('复制失败:', error)
    }
  }

  return (
    <div className="app">
      <h1>AI剪贴板助手</h1>
      
      <div className="input-section">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="请输入或复制文本到剪贴板..."
          rows={4}
        />
      </div>

      <div className="actions">
        <button onClick={handleTranslate} disabled={loading || !text}>
          {loading ? '翻译中...' : '翻译'}
        </button>
        <button onClick={handleSummarize} disabled={loading || !text}>
          {loading ? '总结中...' : '总结'}
        </button>
      </div>

      {translated && (
        <div className="result-section">
          <h3>翻译结果</h3>
          <p>{translated}</p>
          <button onClick={() => handleCopy(translated)}>复制</button>
        </div>
      )}

      {summarized && (
        <div className="result-section">
          <h3>总结结果</h3>
          <p>{summarized}</p>
          <button onClick={() => handleCopy(summarized)}>复制</button>
        </div>
      )}

      <div className="config-section">
        <h3>配置</h3>
        <pre>{JSON.stringify(config, null, 2)}</pre>
      </div>
    </div>
  )
}

export default App

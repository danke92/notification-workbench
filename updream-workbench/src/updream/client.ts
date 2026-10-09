import type {
  GenerationRequest,
  GenerationProgress,
  UPDreamResponse,
  CharacterPortrait,
  Scene,
  VideoContent,
} from '@/types';

// UPDream客户端配置
const CONFIG = {
  // 假设updream本地服务运行在localhost:8000
  API_BASE_URL: process.env.NEXT_PUBLIC_UPDREAM_URL || 'http://localhost:8000',
  TIMEOUT: 60000, // 60秒超时
};

class UPDreamClient {
  private baseUrl: string;

  constructor(baseUrl: string = CONFIG.API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * 生成人物三视图
   */
  async generatePortrait(
    prompt: string,
    options?: { style?: string; age?: string; gender?: string }
  ): Promise<UPDreamResponse<CharacterPortrait>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/portrait/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt,
          type: 'portrait',
          options,
        }),
        signal: AbortSignal.timeout(CONFIG.TIMEOUT),
      });

      if (!response.ok) {
        throw new Error(`UPDream API error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      return {
        success: true,
        data,
      };
    } catch (error) {
      console.error('Failed to generate portrait:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * 生成场景（白模或效果图）
   */
  async generateScene(
    prompt: string,
    type: 'white_model' | 'rendered' | 'concept',
    options?: { mood?: string; lighting?: string }
  ): Promise<UPDreamResponse<Scene>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/scene/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt,
          type,
          options,
        }),
        signal: AbortSignal.timeout(CONFIG.TIMEOUT),
      });

      if (!response.ok) {
        throw new Error(`UPDream API error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      return {
        success: true,
        data,
      };
    } catch (error) {
      console.error('Failed to generate scene:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * 生成视频内容
   */
  async generateVideo(
    prompt: string,
    type: 'character' | 'scene' | 'sequence' | 'animation',
    options?: { duration?: number; resolution?: string; frames?: number }
  ): Promise<UPDreamResponse<VideoContent>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/video/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt,
          type,
          options,
        }),
        signal: AbortSignal.timeout(CONFIG.TIMEOUT),
      });

      if (!response.ok) {
        throw new Error(`UPDream API error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      return {
        success: true,
        data,
      };
    } catch (error) {
      console.error('Failed to generate video:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * 获取生成进度
   */
  async getGenerationProgress(
    generationId: string
  ): Promise<UPDreamResponse<GenerationProgress>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/generation/${generationId}/progress`, {
        signal: AbortSignal.timeout(CONFIG.TIMEOUT),
      });

      if (!response.ok) {
        throw new Error(`UPDream API error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      return {
        success: true,
        data,
      };
    } catch (error) {
      console.error('Failed to get generation progress:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * 测试连接
   */
  async testConnection(): Promise<UPDreamResponse<{ status: string; version?: string }>> {
    try {
      const response = await fetch(`${this.baseUrl}/api/health`, {
        signal: AbortSignal.timeout(5000),
      });

      if (!response.ok) {
        throw new Error(`UPDream API error: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();
      return {
        success: true,
        data,
      };
    } catch (error) {
      console.error('Failed to connect to UPDream:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }
}

// 导出单例实例
export const updreamClient = new UPDreamClient();

// 导出类型以便在其他地方使用
export * from '@/types';

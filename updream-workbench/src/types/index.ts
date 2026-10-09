// 基础类型定义
export interface Project {
  id: string;
  name: string;
  description?: string;
  createdAt: string;
  updatedAt: string;
  status: 'draft' | 'generating' | 'completed' | 'failed';
}

// 人物三视图类型
export interface CharacterPortrait {
  id: string;
  projectId: string;
  name: string;
  views: 'front' | 'side' | 'back';
  imageUrl: string;
  prompt: string;
  createdAt: string;
  metadata?: {
    age?: string;
    gender?: string;
    style?: string;
  };
}

// 场景类型
export interface Scene {
  id: string;
  projectId: string;
  name: string;
  type: 'white_model' | 'rendered' | 'concept';
  imageUrl: string;
  prompt: string;
  createdAt: string;
  metadata?: {
    mood?: string;
    lighting?: string;
    style?: string;
  };
}

// 视频内容类型
export interface VideoContent {
  id: string;
  projectId: string;
  name: string;
  type: 'character' | 'scene' | 'sequence' | 'animation';
  duration?: number; // 秒
  resolution?: string; // 1080p, 4K等
  frames?: number;
  prompt: string;
  createdAt: string;
  status: 'pending' | 'generating' | 'completed' | 'failed';
  outputPath?: string;
  thumbnails?: string[];
}

// 项目归档类型
export interface ProjectArchive {
  id: string;
  projectId: string;
  name: string;
  type: 'full_project' | 'character_set' | 'scene_set' | 'video_sequence';
  createdAt: string;
  items: {
    portraits?: CharacterPortrait[];
    scenes?: Scene[];
    videos?: VideoContent[];
  };
  summary?: {
    totalCharacters: number;
    totalScenes: number;
    totalVideos: number;
  };
}

// 可视化数据类型
export interface AnalyticsData {
  totalProjects: number;
  totalVideos: number;
  totalCharacters: number;
  totalScenes: number;
  generationTime: {
    average: number; // 分钟
    byType: Record<string, number>;
  };
  projectStatus: {
    draft: number;
    generating: number;
    completed: number;
    failed: number;
  };
}

// updream API响应类型
export interface UPDreamResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface GenerationRequest {
  prompt: string;
  type: 'portrait' | 'scene' | 'video';
  options?: {
    resolution?: string;
    style?: string;
    duration?: number;
    frames?: number;
  };
}

export interface GenerationProgress {
  id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number; // 0-100
  message: string;
  createdAt: string;
  completedAt?: string;
}

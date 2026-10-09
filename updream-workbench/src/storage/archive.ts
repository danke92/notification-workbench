import type {
  Project,
  CharacterPortrait,
  Scene,
  VideoContent,
  ProjectArchive,
} from '@/types';

// 存储配置
const STORAGE_CONFIG = {
  BASE_DIR: process.env.NEXT_PUBLIC_STORAGE_DIR || './storage',
  PROJECTS_DIR: 'projects',
  ARCHIVES_DIR: 'archives',
  IMAGES_DIR: 'images',
  VIDEOS_DIR: 'videos',
  THUMBNAILS_DIR: 'thumbnails',
};

/**
 * 存储管理类
 */
class StorageManager {
  private baseDir: string;

  constructor(baseDir: string = STORAGE_CONFIG.BASE_DIR) {
    this.baseDir = baseDir;
  }

  /**
   * 初始化存储目录结构
   */
  async initialize(): Promise<void> {
    try {
      // 这里可以添加创建目录的逻辑
      // 在实际应用中，可能需要使用fs-extra等库
      console.log('Storage initialized at:', this.baseDir);
    } catch (error) {
      console.error('Failed to initialize storage:', error);
      throw error;
    }
  }

  /**
   * 获取项目存储路径
   */
  getProjectPath(projectId: string): string {
    return `${this.baseDir}/${STORAGE_CONFIG.PROJECTS_DIR}/${projectId}`;
  }

  /**
   * 获取归档存储路径
   */
  getArchivePath(archiveId: string): string {
    return `${this.baseDir}/${STORAGE_CONFIG.ARCHIVES_DIR}/${archiveId}`;
  }

  /**
   * 获取图片存储路径
   */
  getImagePath(projectId: string, imageId: string): string {
    return `${this.getProjectPath(projectId)}/${STORAGE_CONFIG.IMAGES_DIR}/${imageId}`;
  }

  /**
   * 获取视频存储路径
   */
  getVideoPath(projectId: string, videoId: string): string {
    return `${this.getProjectPath(projectId)}/${STORAGE_CONFIG.VIDEOS_DIR}/${videoId}`;
  }

  /**
   * 获取缩略图存储路径
   */
  getThumbnailPath(projectId: string, videoId: string): string {
    return `${this.getProjectPath(projectId)}/${STORAGE_CONFIG.THUMBNAILS_DIR}/${videoId}`;
  }

  /**
   * 保存项目
   */
  async saveProject(project: Project): Promise<void> {
    try {
      // 在实际应用中，这里可以写入JSON文件或数据库
      console.log('Saving project:', project.id, project.name);
    } catch (error) {
      console.error('Failed to save project:', error);
      throw error;
    }
  }

  /**
   * 获取所有项目
   */
  async getAllProjects(): Promise<Project[]> {
    try {
      // 在实际应用中，这里可以从JSON文件或数据库读取
      return [];
    } catch (error) {
      console.error('Failed to get projects:', error);
      throw error;
    }
  }

  /**
   * 保存人物三视图
   */
  async savePortrait(portrait: CharacterPortrait): Promise<void> {
    try {
      console.log('Saving portrait:', portrait.id, portrait.name);
    } catch (error) {
      console.error('Failed to save portrait:', error);
      throw error;
    }
  }

  /**
   * 保存场景
   */
  async saveScene(scene: Scene): Promise<void> {
    try {
      console.log('Saving scene:', scene.id, scene.name);
    } catch (error) {
      console.error('Failed to save scene:', error);
      throw error;
    }
  }

  /**
   * 保存视频内容
   */
  async saveVideo(video: VideoContent): Promise<void> {
    try {
      console.log('Saving video:', video.id, video.name);
    } catch (error) {
      console.error('Failed to save video:', error);
      throw error;
    }
  }

  /**
   * 创建项目归档
   */
  async createProjectArchive(
    projectId: string,
    archiveType: ProjectArchive['type'],
    items: ProjectArchive['items']
  ): Promise<ProjectArchive> {
    try {
      const archiveId = `archive_${Date.now()}`;
      const archive: ProjectArchive = {
        id: archiveId,
        projectId,
        name: `${archiveType}_${new Date().toISOString().split('T')[0]}`,
        type: archiveType,
        createdAt: new Date().toISOString(),
        items,
        summary: {
          totalCharacters: items.portraits?.length || 0,
          totalScenes: items.scenes?.length || 0,
          totalVideos: items.videos?.length || 0,
        },
      };

      console.log('Creating archive:', archiveId, archiveType);
      return archive;
    } catch (error) {
      console.error('Failed to create archive:', error);
      throw error;
    }
  }

  /**
   * 获取项目归档
   */
  async getProjectArchives(projectId: string): Promise<ProjectArchive[]> {
    try {
      // 在实际应用中，这里可以从JSON文件或数据库读取
      return [];
    } catch (error) {
      console.error('Failed to get archives:', error);
      throw error;
    }
  }
}

// 导出单例实例
export const storageManager = new StorageManager();

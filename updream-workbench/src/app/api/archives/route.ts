import { NextRequest, NextResponse } from 'next/server';
import { storageManager } from '@/storage/archive';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { projectId, archiveType, items } = body;

    if (!projectId || !archiveType || !items) {
      return NextResponse.json(
        { success: false, error: 'projectId, archiveType, and items are required' },
        { status: 400 }
      );
    }

    // 验证归档类型
    const validTypes = ['full_project', 'character_set', 'scene_set', 'video_sequence'];
    if (!validTypes.includes(archiveType)) {
      return NextResponse.json(
        { success: false, error: `Invalid archive type. Must be one of: ${validTypes.join(', ')}` },
        { status: 400 }
      );
    }

    // 创建归档
    const archive = await storageManager.createProjectArchive(
      projectId,
      archiveType as any,
      items
    );

    return NextResponse.json({
      success: true,
      data: archive,
    });
  } catch (error) {
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const projectId = searchParams.get('projectId');

    if (!projectId) {
      return NextResponse.json(
        { success: false, error: 'projectId is required' },
        { status: 400 }
      );
    }

    // 获取项目的所有归档
    const archives = await storageManager.getProjectArchives(projectId);

    return NextResponse.json({
      success: true,
      data: archives,
    });
  } catch (error) {
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

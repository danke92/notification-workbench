import { NextRequest, NextResponse } from 'next/server';
import { updreamClient } from '@/updream/client';
import { storageManager } from '@/storage/archive';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { prompt, type, options } = body;

    if (!prompt || !type) {
      return NextResponse.json(
        { success: false, error: 'Prompt and type are required' },
        { status: 400 }
      );
    }

    // 验证类型
    const validTypes = ['white_model', 'rendered', 'concept'];
    if (!validTypes.includes(type)) {
      return NextResponse.json(
        { success: false, error: `Invalid type. Must be one of: ${validTypes.join(', ')}` },
        { status: 400 }
      );
    }

    // 调用UPDream生成场景
    const response = await updreamClient.generateScene(prompt, type, options);

    if (!response.success || !response.data) {
      return NextResponse.json(
        { success: false, error: response.error || 'Generation failed' },
        { status: 500 }
      );
    }

    const scene = response.data;

    // 保存到存储
    await storageManager.saveScene(scene);

    return NextResponse.json({
      success: true,
      data: scene,
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

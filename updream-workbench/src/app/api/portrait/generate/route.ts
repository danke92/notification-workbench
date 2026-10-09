import { NextRequest, NextResponse } from 'next/server';
import { updreamClient } from '@/updream/client';
import { storageManager } from '@/storage/archive';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { prompt, options } = body;

    if (!prompt) {
      return NextResponse.json(
        { success: false, error: 'Prompt is required' },
        { status: 400 }
      );
    }

    // 调用UPDream生成人物三视图
    const response = await updreamClient.generatePortrait(prompt, options);

    if (!response.success || !response.data) {
      return NextResponse.json(
        { success: false, error: response.error || 'Generation failed' },
        { status: 500 }
      );
    }

    const portrait = response.data;

    // 保存到存储
    await storageManager.savePortrait(portrait);

    return NextResponse.json({
      success: true,
      data: portrait,
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

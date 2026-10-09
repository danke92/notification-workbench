import { NextResponse } from 'next/server';
import { updreamClient } from '@/updream/client';

export async function GET() {
  try {
    const response = await updreamClient.testConnection();

    if (response.success && response.data) {
      return NextResponse.json({
        status: 'healthy',
        updream: response.data,
        timestamp: new Date().toISOString(),
      });
    } else {
      return NextResponse.json(
        {
          status: 'unhealthy',
          updream: response.error || 'Connection failed',
          timestamp: new Date().toISOString(),
        },
        { status: 503 }
      );
    }
  } catch (error) {
    return NextResponse.json(
      {
        status: 'unhealthy',
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: new Date().toISOString(),
      },
      { status: 503 }
    );
  }
}

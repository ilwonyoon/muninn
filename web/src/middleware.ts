import { NextRequest, NextResponse } from 'next/server'

export function middleware(request: NextRequest) {
  const apiKey = process.env.MUNINN_API_KEY

  // Allow bypass only in development when no API key is configured
  if (!apiKey) {
    if (process.env.NODE_ENV === 'development') {
      return NextResponse.next()
    }

    return NextResponse.json(
      { error: 'MUNINN_API_KEY not configured' },
      { status: 500 }
    )
  }

  // Check x-api-key header first
  const headerKey = request.headers.get('x-api-key')
  if (headerKey === apiKey) {
    return NextResponse.next()
  }

  // Check Authorization: Bearer header
  const authHeader = request.headers.get('authorization')
  if (authHeader && authHeader.startsWith('Bearer ')) {
    const token = authHeader.slice('Bearer '.length)
    if (token === apiKey) {
      return NextResponse.next()
    }
  }

  // Unauthorized
  return NextResponse.json(
    { error: 'Unauthorized', code: 'UNAUTHORIZED' },
    { status: 401 }
  )
}

export const config = {
  matcher: ['/api/:path*'],
}

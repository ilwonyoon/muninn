import { NextRequest, NextResponse } from 'next/server'

export function middleware(request: NextRequest) {
  const apiKey = process.env.MUNINN_API_KEY

  // Allow all requests if no API key is configured (dev mode)
  if (!apiKey) {
    return NextResponse.next()
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

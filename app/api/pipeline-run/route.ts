import { NextRequest, NextResponse } from 'next/server'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    
    // Console.log přijatých dat
    console.log('API endpoint /api/pipeline-run přijal data:', {
      topic: body.topic,
      csv: body.csv || null
    })
    
    // JSON odpověď
    return NextResponse.json({
      status: "received",
      topic: body.topic || "",
      csv: body.csv || null
    })
    
  } catch (error) {
    console.error('Chyba při zpracování API požadavku:', error)
    
    return NextResponse.json({
      status: "error",
      message: "Neplatný požadavek"
    }, { status: 400 })
  }
} 
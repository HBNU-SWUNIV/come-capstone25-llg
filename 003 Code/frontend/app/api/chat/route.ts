import { NextResponse } from "next/server"

export async function POST(req: Request) {
  // 프론트에서 오는 메시지 타입
  type Message = {
    id: string
    role: "user" | "assistant"
    content?: string
    consultantMode?: boolean
  }

  // 백엔드(ki-api) 응답 타입
  type BackendAssistantResponse = {
    id?: string
    role?: "assistant" | "user"
    content?: string
    answer?: string
    session_id?: string
    images?: {
      id: string
      index: number
      base64: string
    }[]
  }

  // 프론트로 되돌려 줄 assistant 메시지 타입
  type FrontMessage = {
    id: string
    role: "user" | "assistant"
    content: string
    consultantMode?: boolean
    images?: {
      id: string
      index: number
      base64: string
    }[]
  }

  try {
    // 🔥 page.tsx에서 보내는 body: { messages, sessionId, isConsultantMode }
    const {
      messages,
      sessionId,
      isConsultantMode,
    }: {
      messages: Message[]
      sessionId?: string | null
      isConsultantMode?: boolean
    } = await req.json()

    const filteredMessages = messages
      .filter((msg: Message) => msg.content !== undefined)
      .filter((msg: Message) => msg.role === "user")
      .map((msg: Message) => ({
        role: msg.role,
        content: msg.content as string,
        consultantMode: msg.consultantMode ?? false,
      }))

    const lastConsultantMode =
      typeof isConsultantMode === "boolean"
        ? isConsultantMode
        : filteredMessages.length > 0
          ? filteredMessages[filteredMessages.length - 1].consultantMode
          : false

    const response = await fetch("http://ki-api:8000/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        messages: filteredMessages,
        sessionId: sessionId ?? null,
        isConsultantMode: lastConsultantMode,
      }),
    })

    const data: BackendAssistantResponse = await response.json()
    console.log("ki-api /chat 응답:", data)

    const assistantMessage: FrontMessage = {
      id: data.id ?? crypto.randomUUID(),
      role: "assistant",
      content: data.content ?? data.answer ?? "",
      images: data.images ?? [],
    }

    return NextResponse.json({
      messages: [assistantMessage],
      session_id: data.session_id ?? null,
    })
  } catch (error) {
    console.error("채팅 API 오류:", error)
    return new Response("서버 오류가 발생했습니다", { status: 500 })
  }
}

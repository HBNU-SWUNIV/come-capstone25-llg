"use client"

import { useState, useRef, useEffect } from "react"
import type React from "react"

// UI Components
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { 
  Loader2, 
  Hash, 
  Send, 
  Bot, 
  User, 
  Sparkles, 
  GraduationCap,
  Menu,
  Plus,
  MessageSquare,
  X,
  Trash2,
  MoreHorizontal,
  Maximize2 
} from "lucide-react"


// --- 타입 정의 ---
type ImageItem = {
  id: string
  index: number
  base64: string
}

export type Message = {
  id: string
  role: "user" | "assistant"
  content?: string
  consultantMode?: boolean
  images?: ImageItem[]
}

// 채팅 세션(내역) 타입
type ChatSession = {
  id: string
  title: string
  date: string
  preview: string
  isConsultant: boolean
}

export default function ChatbotInterface() {
  // --- State ---
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  
  const [isConsultantMode, setIsConsultantMode] = useState(true)
  
  // 사이드바 & 채팅 세션 관리
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [chatHistory, setChatHistory] = useState<ChatSession[]>([]) 
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)

  // 🔥 이미지 확대 모달용 State
  const [selectedImage, setSelectedImage] = useState<string | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)

  // --- Effects ---
  useEffect(() => {
    fetchSessions()
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])


  // --- API Functions ---
  const fetchSessions = async () => {
    try {
      const res = await fetch("http://localhost:8000/sessions")
      if (res.ok) {
        const data = await res.json()
        setChatHistory(data)
      }
    } catch (error) {
      console.error("세션 목록 로드 실패:", error)
    }
  }

  // --- Handlers ---
  const handleConsultantClick = () => setIsConsultantMode(!isConsultantMode)
  const toggleSidebar = () => setIsSidebarOpen(!isSidebarOpen)

  const startNewChat = () => {
    setMessages([])
    setCurrentSessionId(null)
    setInput("")
    setIsConsultantMode(true) 
    if (window.innerWidth < 768) setIsSidebarOpen(false)
  }

  const selectChat = async (session: ChatSession) => {
    setCurrentSessionId(session.id)
    setIsConsultantMode(session.isConsultant)
    
    try {
      const res = await fetch(`http://localhost:8000/sessions/${session.id}/messages`)
      if (res.ok) {
        const historyMessages = await res.json()
        setMessages(historyMessages)
      }
    } catch (error) {
      console.error("메시지 내역 로드 실패:", error)
    }
    
    if (window.innerWidth < 768) setIsSidebarOpen(false)
  }

  const handleDeleteHistory = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    if (!confirm("정말 이 채팅 기록을 삭제하시겠습니까?")) return

    try {
      const res = await fetch(`http://localhost:8000/sessions/${id}`, { method: "DELETE" })
      if (res.ok) {
        setChatHistory(prev => prev.filter(item => item.id !== id))
        if (currentSessionId === id) startNewChat()
      }
    } catch (error) {
      console.error("삭제 실패:", error)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      consultantMode: isConsultantMode,
    }

    setMessages((prev) => [...prev, userMessage])
    setInput("")
    setIsLoading(true)

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [userMessage],
          sessionId: currentSessionId,
          isConsultantMode: isConsultantMode,
        }),
      })

      if (!response.ok) throw new Error("API 응답 오류")

      const data: { messages: Message[]; session_id?: string | null } = await response.json()

      if (data.session_id && data.session_id !== currentSessionId) {
        setCurrentSessionId(data.session_id)
        fetchSessions()
      }

      const assistantMessages = data.messages ?? []
      if (assistantMessages.length > 0) {
        const assistantMessage = assistantMessages[0]
        setMessages((prev) => [...prev, assistantMessage])
      }
    } catch (error) {
      console.error("메시지 전송 오류:", error)
    } finally {
      setIsLoading(false)
    }
  }


  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden relative">
      
      {/* 🔥 이미지 확대 모달 (z-index 최상위) */}
      {selectedImage && (
        <div 
          className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/95 backdrop-blur-sm animate-in fade-in duration-200"
          onClick={(e) => {
            e.stopPropagation()
            setSelectedImage(null)
          }} 
        >
          {/* 닫기 버튼 */}
          <Button
            variant="ghost"
            size="icon"
            className="absolute top-5 right-5 text-white/70 hover:text-white hover:bg-white/10 h-12 w-12 rounded-full z-[10000]"
            onClick={(e) => {
              e.stopPropagation()
              setSelectedImage(null)
            }}
          >
            <X className="h-8 w-8" />
          </Button>

          {/* 확대된 이미지 */}
          <div 
            className="relative flex items-center justify-center w-full h-full p-4"
            onClick={(e) => e.stopPropagation()} 
          >
            <img 
              src={`data:image/png;base64,${selectedImage}`} 
              alt="Full view" 
              className="max-w-full max-h-[90vh] object-contain rounded-md shadow-2xl"
            />
          </div>
        </div>
      )}

      {/* --- 사이드바 (Chat History) --- */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-30 md:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      <aside 
        className={`
          fixed md:relative z-40 flex flex-col h-full w-[280px] bg-white border-r border-slate-200 transition-transform duration-300 ease-in-out
          ${isSidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
        `}
      >
        <div className="p-4 h-16 flex items-center justify-between border-b border-slate-100">
          <h2 className="font-semibold text-slate-700 flex items-center gap-2">
            <GraduationCap className="h-5 w-5 text-indigo-600" />
            채팅 기록
          </h2>
          <Button variant="ghost" size="icon" className="md:hidden" onClick={toggleSidebar}>
            <X className="h-5 w-5" />
          </Button>
        </div>

        <div className="p-3">
          <Button 
            onClick={startNewChat}
            className="w-full justify-start gap-2 bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm"
          >
            <Plus className="h-4 w-4" />
            새로운 채팅
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
          <div className="text-xs font-medium text-slate-400 px-2 py-2 mb-1">최근 상담</div>
          
          {chatHistory.length === 0 ? (
            <div className="text-center text-xs text-slate-400 py-4">기록이 없습니다.</div>
          ) : (
            chatHistory.map((session) => (
              <div
                key={session.id}
                onClick={() => selectChat(session)}
                className={`
                  group flex items-center gap-3 px-3 py-3 rounded-lg cursor-pointer transition-all
                  ${currentSessionId === session.id 
                    ? "bg-indigo-50 text-indigo-900 shadow-sm border border-indigo-100" 
                    : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"}
                `}
              >
                <div className={`mt-0.5 text-indigo-500`}>
                  <GraduationCap className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0 overflow-hidden">
                  <div className="flex justify-between items-center mb-0.5">
                    <span className="text-sm font-medium truncate">{session.title}</span>
                  </div>
                  <p className="text-xs text-muted-foreground truncate opacity-80">
                    {session.preview}
                  </p>
                </div>
                
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity text-slate-400 hover:text-red-500"
                  onClick={(e) => handleDeleteHistory(e, session.id)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            ))
          )}
        </div>

        <div className="p-4 border-t border-slate-100">
          <div className="flex items-center gap-3 px-2 py-2 rounded-lg hover:bg-slate-50 cursor-pointer transition-colors">
            <Avatar className="h-8 w-8 bg-indigo-100">
              <AvatarFallback><User className="h-4 w-4 text-indigo-600"/></AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-700">수험생</p>
              <p className="text-xs text-slate-400 truncate">student@example.com</p>
            </div>
            <MoreHorizontal className="h-4 w-4 text-slate-400" />
          </div>
        </div>
      </aside>


      {/* --- 메인 컨텐츠 영역 --- */}
      <div className="flex-1 flex flex-col h-full w-full relative">
        
        <header className="flex-none h-16 bg-white/80 backdrop-blur-md border-b border-slate-200 flex items-center justify-between px-4 md:px-6 z-10">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" className="md:hidden -ml-2" onClick={toggleSidebar}>
              <Menu className="h-5 w-5" />
            </Button>
            
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg transition-colors duration-300 bg-indigo-600">
                <GraduationCap className="h-4 w-4 text-white" />
              </div>
              <div>
                <h1 className="font-bold text-base md:text-lg tracking-tight leading-none">
                  LLG Chatbot
                </h1>
                <span className="text-[10px] md:text-xs text-muted-foreground">
                  Professional Consultant
                </span>
              </div>
            </div>
          </div>

          <div className="hidden md:flex items-center text-indigo-600 bg-indigo-50 px-3 py-1 rounded-full text-xs font-medium border border-indigo-100">
            <Sparkles className="h-3 w-3 mr-1.5" />
          </div>
        </header>

        {/* 메인 채팅 영역 */}
        <main className="flex-1 overflow-hidden relative bg-slate-50/50">
          <div className="h-full overflow-y-auto scroll-smooth px-4 py-6 container max-w-5xl mx-auto">
            
            {/* Empty State */}
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center space-y-6 opacity-0 animate-in fade-in zoom-in duration-500">
                <div className="relative">
                  <div className="absolute inset-0 blur-3xl opacity-20 rounded-full bg-indigo-500" />
                  <div className="relative p-6 rounded-2xl shadow-xl bg-white border-indigo-100 border">
                    <GraduationCap className="h-10 w-10 text-indigo-600" />
                  </div>
                </div>
                <div className="max-w-sm">
                  <h2 className="text-xl font-bold mb-2">
                    입시 상담을 시작하세요
                  </h2>
                  <p className="text-sm text-muted-foreground">
                    대학 입시, 전형 분석, 생기부 관리 등<br/>전문적인 입시 정보를 물어보세요.
                  </p>
                </div>
              </div>
            )}

            {/* 메시지 리스트 */}
            <div className="space-y-6 pb-4">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex w-full ${message.role === "user" ? "justify-end" : "justify-start"} animate-in slide-in-from-bottom-2 duration-300`}
                >
                  <div className={`flex items-start gap-2 md:gap-3 max-w-[90%] md:max-w-[80%] ${message.role === "user" ? "flex-row-reverse" : ""}`}>
                    
                    <Avatar className={`h-8 w-8 border shadow-sm mt-1 hidden md:flex ${message.role === "assistant" ? "bg-white" : "bg-indigo-900"}`}>
                      {message.role === "user" ? (
                        <AvatarFallback className="bg-indigo-900 text-white"><User className="h-4 w-4" /></AvatarFallback>
                      ) : (
                        <AvatarFallback className="bg-indigo-50 text-indigo-600">
                           <GraduationCap className="h-4 w-4"/>
                        </AvatarFallback>
                      )}
                    </Avatar>

                    {/* 🔥 메시지 컨텐츠 래퍼 (말풍선 + 이미지) */}
                    <div className="flex flex-col gap-1">
                      {message.role === "user" && (
                        <span className="text-[10px] font-medium text-indigo-600 self-end bg-indigo-50 px-2 py-0.5 rounded-full border border-indigo-100 mb-1">
                          {/* 입시질문 */}
                        </span>
                      )}
                      
                      {/* 1. 텍스트 말풍선 */}
                      <div
                        className={`relative px-4 py-3 text-sm leading-relaxed shadow-sm
                          ${message.role === "user" 
                            ? "bg-indigo-600 text-white rounded-2xl rounded-tr-sm [&_a]:text-indigo-100" 
                            : "bg-white border border-slate-100 text-slate-800 rounded-2xl rounded-tl-sm [&_a]:text-indigo-600"
                          }
                        `}
                      >
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            ul: ({ node, ...props }) => (
                              <ul className="list-disc pl-4 my-2 space-y-1" {...props} />
                            ),
                            ol: ({ node, ...props }) => (
                              <ol className="list-decimal pl-4 my-2 space-y-1" {...props} />
                            ),
                            li: ({ node, ...props }) => <li className="pl-1" {...props} />,
                            p: ({ node, ...props }) => (
                              <p className="mb-2 last:mb-0 whitespace-pre-wrap" {...props} />
                            ),
                            strong: ({ node, ...props }) => <span className="font-bold" {...props} />,
                            a: ({ node, ...props }) => (
                              <a
                                className="underline underline-offset-2 font-medium hover:opacity-80 transition-opacity"
                                target="_blank"
                                rel="noopener noreferrer"
                                {...props}
                              />
                            ),
                            code: ({ node, ...props }) => (
                              <code
                                className="bg-black/10 rounded px-1.5 py-0.5 font-mono text-[0.9em]"
                                {...props}
                              />
                            ),
                          }}
                        >
                          {message.content || ""}
                        </ReactMarkdown>
                      </div>

                      {/* 2. 이미지 영역 (말풍선 밖으로 분리됨 - 클릭 문제 해결) */}
                      {message.role === "assistant" && message.images && message.images.length > 0 && (
                        <div className="mt-2 grid grid-cols-2 gap-2 w-fit max-w-full">
                          {message.images.map((img) => (
                            <div
                              key={img.id}
                              className="group relative border border-slate-200 rounded-lg overflow-hidden bg-white cursor-pointer hover:ring-2 hover:ring-indigo-300 transition-all shadow-sm"
                              onClick={(e) => {
                                e.preventDefault()
                                e.stopPropagation()
                                console.log("이미지 클릭됨:", img.id)
                                setSelectedImage(img.base64)
                              }}
                            >
                              <img
                                src={`data:image/png;base64,${img.base64}`}
                                alt={img.id}
                                className="w-full h-40 object-cover bg-white group-hover:scale-105 transition-transform duration-300"
                              />
                              
                              {/* pointer-events-none 추가하여 클릭 투과 */}
                              <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 bg-black/30 transition-opacity pointer-events-none">
                                <Maximize2 className="h-8 w-8 text-white drop-shadow-md" />
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}

              {/* 로딩 인디케이터 */}
              {isLoading && (
                <div className="flex justify-start animate-in fade-in duration-300">
                  <div className="flex items-end gap-3">
                    <Avatar className="h-8 w-8 border bg-white hidden md:flex">
                      <AvatarFallback><GraduationCap className="h-4 w-4 text-indigo-600"/></AvatarFallback>
                    </Avatar>
                    <div className="bg-white border border-slate-100 px-4 py-3 rounded-2xl rounded-tl-sm shadow-sm flex items-center gap-1">
                      <span className="h-1.5 w-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                      <span className="h-1.5 w-1.5 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                      <span className="h-1.5 w-1.5 bg-indigo-400 rounded-full animate-bounce"></span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </div>
        </main>

        {/* 입력 영역 */}
        <div className="flex-none bg-white/80 backdrop-blur-lg border-t p-4">
          <div className="container max-w-5xl mx-auto">
            <form 
              onSubmit={handleSubmit} 
              className="relative flex items-center gap-2 p-2 rounded-full border shadow-sm focus-within:ring-2 transition-all duration-300 focus-within:ring-indigo-100 border-indigo-200 bg-indigo-50/30"
            >
              <div className="pl-3 hidden md:block">
               <Hash className="h-4 w-4 text-indigo-400" />
              </div>
              
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="입시 관련 궁금한 점을 물어보세요..."
                className="flex-1 border-0 bg-transparent focus-visible:ring-0 px-2 py-2 h-auto shadow-none placeholder:text-slate-400 text-black text-sm md:text-base"
                disabled={isLoading}
              />
              
              <Button 
                type="submit" 
                size="icon"
                disabled={isLoading || !input.trim()}
                className={`rounded-full h-9 w-9 md:h-10 md:w-10 transition-all ${
                  !input.trim() 
                    ? "opacity-50 bg-slate-200 text-slate-400" 
                    : "bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-200"
                }`}
              >
                {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4 ml-0.5" />}
              </Button>
            </form>
            <div className="text-center mt-2">
              <p className="text-[10px] text-slate-400">AI는 실수를 할 수 있습니다. 중요 정보는 확인하세요.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
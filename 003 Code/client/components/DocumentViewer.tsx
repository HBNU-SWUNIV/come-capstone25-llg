import { useState, useEffect } from "react";
// lucide-react에서 'ImageIcon'은 존재하지 않을 수 있어 'Image'를 'ImageIcon'으로 별칭 사용
import { Download, FileText, Image as ImageIcon, X, Edit2, Trash2, Maximize2 } from "lucide-react";

// --- Interfaces ---
interface TextChunk {
  id: string;
  content: string;
  chunk_index: number;
  metadata?: any;
}

interface PDFImage {
  id: string;
  index: number;
  src: string;
}

interface DocumentViewerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  textChunks: TextChunk[];
  images: PDFImage[];
  onDownloadPdf: () => void;
  onSaveTextChunk: (id: string, newContent: string) => Promise<void>;
  onDeleteTextChunk?: (id: string) => Promise<void>;
  onDeleteImage?: (id: string) => Promise<void>;
}

// --- Helper Components ---
function Badge({ children, variant = "default", className = "" }: any) {
  const base = "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold";
  const variants: any = {
    default: "border-transparent bg-slate-900 text-black",
    secondary: "border-transparent bg-slate-100 text-slate-900",
    outline: "text-slate-500 border-slate-200",
  };
  return <span className={`${base} ${variants[variant]} ${className}`}>{children}</span>;
}

function Button({ children, onClick, variant = "default", size = "default", className = "", disabled = false, title = "" }: any) {
  const base = "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed";
  const variants: any = {
    default: "bg-slate-900 text-black hover:bg-slate-800",
    outline: "border border-slate-200 bg-white text-slate-700 hover:bg-slate-100",
    ghost: "hover:bg-slate-100 hover:text-slate-900",
    destructive: "bg-red-600 text-white hover:bg-red-700",
  };
  const sizes: any = {
    default: "h-10 px-4 py-2",
    sm: "h-9 rounded-md px-3",
    icon: "h-10 w-10",
  };
  return (
    <button type="button" onClick={onClick} disabled={disabled} className={`${base} ${variants[variant]} ${sizes[size]} ${className}`} title={title}>
      {children}
    </button>
  );
}

// --- Main Component ---
export function DocumentViewer({
  isOpen,
  onClose,
  title,
  textChunks = [],
  images = [],
  onDownloadPdf,
  onSaveTextChunk,
  onDeleteTextChunk,
  onDeleteImage,
}: DocumentViewerProps) {
  const [activeTab, setActiveTab] = useState<"text" | "images" | null>(null);
  
  // Text State
  const [editingChunkId, setEditingChunkId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [localChunks, setLocalChunks] = useState<TextChunk[]>(textChunks);

  // Image State
  const [localImages, setLocalImages] = useState<PDFImage[]>(images);
  const [selectedImage, setSelectedImage] = useState<PDFImage | null>(null);

  useEffect(() => {
    setLocalChunks(textChunks ?? []);
  }, [textChunks]);

  useEffect(() => {
    setLocalImages(images ?? []);
  }, [images]);

  useEffect(() => {
    if (isOpen) {
      setActiveTab(null);
      setEditingChunkId(null);
      setEditContent("");
      setIsSaving(false);
      setSelectedImage(null);
    }
  }, [isOpen]);

  // --- Handlers ---
  const handleEditClick = (chunk: TextChunk) => {
    setEditingChunkId(chunk.id);
    setEditContent(chunk.content ?? "");
  };

  const handleDeleteClick = async (id: string) => {
    if (window.confirm("정말 이 텍스트 청크를 삭제하시겠습니까?")) {
      if (onDeleteTextChunk) {
        await onDeleteTextChunk(id);
      }
      setLocalChunks((prev) => prev.filter((c) => c.id !== id));
    }
  };

  const handleSave = async () => {
    if (!editingChunkId) return;
    setIsSaving(true);
    try {
      await onSaveTextChunk(editingChunkId, editContent);
      setLocalChunks(prev => prev.map(c => (c.id === editingChunkId ? { ...c, content: editContent } : c)));
      setEditingChunkId(null);
      setEditContent("");
    } finally {
      setIsSaving(false);
    }
  };

  const handleImageClick = (img: PDFImage) => {
    setSelectedImage(img);
  };

  const handleCloseLightbox = () => {
    setSelectedImage(null);
  };

  const handleDownloadImage = (img: PDFImage) => {
    const link = document.createElement("a");
    link.href = img.src;
    link.download = `image-${img.index + 1}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDeleteImage = async (id: string) => {
    if (window.confirm("정말 이 이미지를 삭제하시겠습니까?")) {
      try {
        if (onDeleteImage) {
          await onDeleteImage(id);
        }
        setLocalImages((prev) => prev.filter((img) => img.id !== id));
        setSelectedImage(null);
      } catch (error) {
        console.error("이미지 삭제 실패", error);
        alert("이미지 삭제 중 오류가 발생했습니다.");
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm grid place-items-center p-4">
      {/* 모달 박스 (relative 필수) 
         이미지 확대 창이 이 박스 안에서만 뜨도록 함
      */}
      <div
        className="bg-white w-full max-w-5xl h-[90vh] rounded-xl shadow-2xl flex flex-col border border-slate-600 overflow-hidden ring-2 ring-slate-50 relative"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-500 shrink-0 bg-gradient-to-br from-blue-100 to-indigo-100">
          <div className="flex flex-col gap-1">
            <h2 className="text-xl font-bold flex items-center gap-2 text-slate-900">
              <FileText className="w-5 h-5 text-blue-600" /> {title}
            </h2>
          </div>

          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={onDownloadPdf} className="gap-2">
              <Download className="w-4 h-4" /> PDF 다운로드
            </Button>
            <Button variant="ghost" size="icon" onClick={onClose} className="rounded-full hover:bg-red-50 hover:text-red-600">
              <X className="w-5 h-5" />
            </Button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex px-6 pt-2 bg-slate-50 border-b border-slate-200 shrink-0 gap-2">
          <button
            type="button"
            onClick={() => setActiveTab("text")}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-t-lg transition-all border-t border-x border-b-0 mb-[-1px]
              ${activeTab === "text" ? "bg-white text-blue-700 border-slate-200 border-b-white shadow-sm" : "bg-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-100"}`}
          >
            <FileText className="w-4 h-4" /> 텍스트
            <Badge variant={activeTab === "text" ? "secondary" : "secondary"} className="ml-1">{localChunks.length}</Badge>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab("images")}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-semibold rounded-t-lg transition-all border-t border-x border-b-0 mb-[-1px]
              ${activeTab === "images" ? "bg-white text-blue-700 border-slate-200 border-b-white shadow-sm" : "bg-transparent text-slate-500 hover:text-slate-700 hover:bg-slate-100"}`}
          >
            <ImageIcon className="w-4 h-4" /> 이미지
            <Badge variant={activeTab === "images" ? "secondary" : "secondary"} className="ml-1">{localImages.length}</Badge>
          </button>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 bg-slate-100 p-4 min-h-0 flex flex-col overflow-hidden">
          {activeTab === null && (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-400 gap-3">
              <FileText className="w-12 h-12 opacity-20" />
              <p>상단 탭을 선택하여 내용을 확인하세요.</p>
            </div>
          )}

          {/* 1. TEXT TAB CONTENT */}
          {activeTab === "text" && (
            <div className="w-full max-w-4xl mx-auto flex flex-col h-full">
              <div className="w-full bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full">
                <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between bg-white shrink-0">
                  <div className="text-sm font-bold text-slate-800 pl-4">텍스트</div>
                </div>

                <div className="p-5 overflow-y-auto flex-1 bg-slate-50/50">
                  <div className="space-y-4">
                    {localChunks.map(chunk => (
                      <div
                        key={chunk.id}
                        className={`bg-white p-5 rounded-lg border transition-all shadow-sm ${
                          editingChunkId === chunk.id 
                            ? "ring-2 ring-blue-500 ring-offset-2 border-transparent" 
                            : "border-slate-200 hover:border-blue-300 hover:shadow-md"
                        }`}
                      >
                        <div className="flex items-center justify-between gap-3 mb-3 border-b border-slate-100 pb-2">
                          <div className="flex items-center gap-2">
                            <span className="bg-slate-100 text-slate-600 text-xs font-bold px-2 py-1 rounded">Chunk #{chunk.chunk_index + 1}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            {editingChunkId === chunk.id ? (
                              <>
                                <button 
                                  className="text-xs font-medium px-3 py-1.5 bg-white border border-slate-300 text-slate-600 rounded hover:bg-slate-50 transition-colors" 
                                  onClick={() => { setEditingChunkId(null); setEditContent(""); }}
                                >
                                  취소
                                </button>
                                <button 
                                  className="text-xs font-medium px-3 py-1.5 bg-blue-600 text-black rounded hover:bg-blue-700 shadow-sm transition-colors" 
                                  onClick={handleSave}
                                >
                                  저장
                                </button>
                              </>
                            ) : (
                              <>
                                <button
                                  className="text-slate-400 hover:text-red-600 hover:bg-red-50 p-1.5 rounded transition-all"
                                  onClick={() => handleDeleteClick(chunk.id)}
                                  title="삭제"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                                <button 
                                  className="text-slate-400 hover:text-blue-600 hover:bg-blue-50 p-1.5 rounded transition-all" 
                                  onClick={() => handleEditClick(chunk)}
                                  title="내용 수정"
                                >
                                  <Edit2 className="w-4 h-4" />
                                </button>
                              </>
                            )}
                          </div>
                        </div>

                        <div>
                          {editingChunkId === chunk.id ? (
                            <textarea 
                              className="w-full border border-slate-300 p-3 rounded-md text-sm focus:ring-2 focus:ring-blue-200 focus:border-blue-500 outline-none transition-all leading-relaxed" 
                              rows={8} 
                              value={editContent} 
                              onChange={(e) => setEditContent(e.target.value)} 
                              placeholder="내용을 입력하세요..."
                            />
                          ) : (
                            <div className="text-sm text-slate-700 whitespace-pre-wrap leading-relaxed pl-1">
                              {chunk.content || <span className="text-slate-400 italic">(내용 없음)</span>}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                    {localChunks.length === 0 && (
                      <div className="flex flex-col items-center justify-center py-12 text-slate-400">
                        <FileText className="w-10 h-10 mb-3 opacity-20" />
                        <span>텍스트 데이터가 없습니다.</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 2. IMAGE TAB CONTENT */}
          {activeTab === "images" && (
            <div className="w-full max-w-6xl mx-auto flex flex-col h-full relative">
              <div className="w-full bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden flex flex-col h-full">
                <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between bg-white shrink-0">
                  <div className="text-sm font-bold text-slate-800 pl-4">이미지</div>
                </div>

                <div className="p-5 overflow-y-auto flex-1 bg-slate-50/50">
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
                    {localImages.map(img => (
                      <div 
                        key={img.id} 
                        className="group bg-white rounded-lg border border-slate-200 p-3 shadow-sm hover:shadow-md transition-all hover:-translate-y-0.5 cursor-pointer"
                        onClick={() => handleImageClick(img)}
                      >
                        <div className="flex justify-between items-center mb-2 px-1">
                          <div className="text-xs font-medium text-slate-500">Image #{img.index + 1}</div>
                          <Maximize2 className="w-3.5 h-3.5 text-slate-300 group-hover:text-blue-500 transition-colors" />
                        </div>
                        <div className="aspect-[4/3] bg-slate-100 rounded overflow-hidden border border-slate-100 relative">
                          <img src={img.src} alt={`img-${img.index}`} className="w-full h-full object-contain" />
                          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/5 transition-colors flex items-center justify-center">
                          </div>
                        </div>
                      </div>
                    ))}
                    {localImages.length === 0 && (
                      <div className="col-span-full flex flex-col items-center justify-center py-12 text-slate-400">
                        <ImageIcon className="w-10 h-10 mb-3 opacity-20" />
                        <span>이미지가 없습니다.</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 3. LIGHTBOX (MODAL OVERLAY) */}
        {selectedImage && (
          <div
            // [수정] z-[9999]: 최상단 보장, bg-slate-950/80: 확실한 반투명 검정 배경
            className="fixed inset-0 z-[9999] bg-slate-950/80 backdrop-blur-sm flex items-center justify-center animate-in fade-in duration-300"
            onClick={handleCloseLightbox}
          >
            {/* 팝업 카드 (Modal)
            */}
            <div 
              className="bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col border border-slate-500/50 animate-in zoom-in-95 duration-300 relative"
              style={{ width: '90vmin', height: '90vmin' }}
              onClick={(e) => e.stopPropagation()} 
            >
              
              {/* [헤더] */}
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 bg-slate-200 shrink-0">
                <div className="font-semibold text-slate-800 flex items-center gap-2">
                  <ImageIcon className="w-4 h-4 text-blue-600" />
                  <span>Image</span>
                  <Badge variant="secondary" className="ml-2">#{selectedImage.index + 1}</Badge>
                </div>
                
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleDownloadImage(selectedImage)}
                    className="p-2 text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded-md transition-colors"
                    title="다운로드"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDeleteImage(selectedImage.id)}
                    className="p-2 text-slate-500 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
                    title="삭제"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                  <div className="w-px h-4 bg-slate-300 mx-1"></div>
                  <button
                    onClick={handleCloseLightbox}
                    className="p-2 text-slate-500 hover:text-slate-900 hover:bg-slate-200 rounded-md transition-colors"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
              </div>

              {/* [이미지 영역] 
                  flex-1 w-full h-full: 부모 영역(80vmin)을 가득 채움
                  p-0: 패딩을 완전히 제거하여 이미지를 최대한 크게 표시
              */}
              <div className="flex-1 w-full h-full min-h-0 bg-slate-100 flex items-center justify-center p-0 relative overflow-hidden group">
                 {/* 투명 배경 패턴 */}
                 <div className="absolute inset-0 opacity-[0.03] bg-[radial-gradient(#000_1px,transparent_1px)] [background-size:16px_16px]"></div>
                 
                 {/* 실제 이미지 */}
                 <img
                    src={selectedImage.src}
                    alt={`Detail ${selectedImage.index}`}
                    className="max-w-full max-h-full object-contain shadow-lg transition-transform duration-300 group-hover:scale-[1.02]"
                  />
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
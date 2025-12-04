'use client'; 

import { useState, useEffect, useCallback } from 'react';
import { SidebarProvider } from '../components/ui/sidebar'; 
import { AppSidebar } from '../components/AppSidebar'; 
import { DatabaseConnection } from '../components/DatabaseConnection'; 
import { DocumentGrid } from '../components/DocumentGrid'; 
import { DocumentTable } from '../components/DocumentTable'; 
import { Toaster } from '../components/ui/sonner'; 
import { PDFUploadZone } from '../components/PDFUploadZone'; 
import { LayoutGrid, Table, FolderPlus, ArrowUpDown, Maximize2, Minimize2, Trash2, Search } from 'lucide-react';
import { Button } from '../components/ui/button'; 
import { Badge } from '../components/ui/badge'; 
import { FolderDialog } from '../components/FolderDialog';
import { toast } from 'sonner';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Input } from '../components/ui/input';
import { DocumentViewer } from '../components/DocumentViewer';

declare global {
  interface Window {
    electronAPI: {
      getInitialData: () => Promise<{ folders: Folder[], documents: PDFDocument[] }>;
      connectDB: (config: any) => Promise<boolean>;
      disconnectDB: () => Promise<boolean>;
      openPDFFiles: () => Promise<void>;
      addPDFFiles: (files: FileData[]) => Promise<void>;
      createFolder: (name: string, color: string) => Promise<Folder | null>;
      
      deleteDocument: (id: string, documentName: string) => Promise<void>;
      moveToFolder: (documentId: string, documentName:string, folderId: string | null) => Promise<void>;
      
      deleteDocuments: (ids: string[]) => Promise<{ success: boolean, deletedCount: number }>;
      moveDocuments: (ids: string[], folderName: string | null) => Promise<{ success: boolean, movedCount: number }>;
      
      processDroppedFiles: (paths: string[]) => Promise<void>;


      getDocumentContent: (id: string) => Promise<{ success: boolean, fileName?: string, textChunks?: any[], images?: any[], error?: string }>;
      downloadDocument: (id: string, fileName: string) => Promise<{ success: boolean, filePath?: string, message?: string }>;
      updateTextChunk: (chunkId: string, newContent: string) => Promise<{ success: boolean }>;
      deleteTextChunk: (chunkId: string) => Promise<{ success: boolean }>; 
      deleteImage: (imageId: string) => Promise<{ success: boolean }>;

      onDocumentUpdate: (callback: (updatedDocument: PDFDocument) => void) => () => void;
      onNewDocument: (callback: (newDocument: PDFDocument) => void) => () => void;

      deleteFolder: (folderId: string) => Promise<void>;
    };
  }
}

interface FileData {
  name: string;
  buffer: ArrayBuffer;
}

export interface Folder {
  id: string;
  name: string;
  color: string;
  createdDate: Date;
}

export interface PDFDocument {
  id: string;
  name: string;
  size: number;
  uploadDate: Date;
  status: 'processing' | 'ready' | 'error';
  tags?: string[];
  folderId?: string;
}

console.log('[React App] page.tsx loaded');

export default function App() {
  console.log('[React App] App component rendering/re-rendering');

  const [isConnected, setIsConnected] = useState(false);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [documents, setDocuments] = useState<PDFDocument[]>([]);
  
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');
  const [activeSection, setActiveSection] = useState<'documents' | 'upload' | 'database'>('documents');
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [isFolderDialogOpen, setIsFolderDialogOpen] = useState(false);
  const [sortBy, setSortBy] = useState<'name' | 'date' | 'status' | 'size'>('date');
  const [gridSize, setGridSize] = useState<'small' | 'medium' | 'large'>('medium');

  const [searchQuery, setSearchQuery] = useState('');

  const [isViewerOpen, setIsViewerOpen] = useState(false);
  const [viewingDoc, setViewingDoc] = useState<PDFDocument | null>(null);
  const [viewingContent, setViewingContent] = useState<{ textChunks: any[], images: any[] }>({ textChunks: [], images: [] });

  useEffect(() => {
    console.log('[React App] Initial useEffect running');

    async function loadData() {
      if (window.electronAPI) {
        try {
          const { folders, documents } = await window.electronAPI.getInitialData();
          setFolders(folders);
          setDocuments(documents);
        } catch (e) {
          console.error("[React App] Error calling getInitialData:", e);
          toast.error("데이터를 불러오는 데 실패했습니다.");
        }
      }
    }
    loadData();

    let removeNewDocListener: (() => void) | undefined;
    let removeUpdateDocListener: (() => void) | undefined;

    if (window.electronAPI) {
      removeNewDocListener = window.electronAPI.onNewDocument((newDocument) => {
        setDocuments(prev => [newDocument, ...prev.filter(d => d.id !== newDocument.id)]);
        toast.info(`새 문서 처리 중: ${newDocument.name}`);
      });

      removeUpdateDocListener = window.electronAPI.onDocumentUpdate((updatedDoc) => {
        setDocuments(prev => prev.map(doc => doc.id === updatedDoc.id ? updatedDoc : doc));
        if (updatedDoc.status === 'ready') {
          toast.success(`처리 완료: ${updatedDoc.name}`);
        } else if (updatedDoc.status === 'error') {
          toast.error(`처리 오류: ${updatedDoc.name}`);
        }
      });
    }

    return () => {
      removeNewDocListener?.();
      removeUpdateDocListener?.();
    };
  }, []);

  const handleUploadDrop = async (files: FileData[]) => {
    if (!isConnected) {
       toast.error('문서를 처리하려면 먼저 데이터베이스에 연결해주세요');
       return;
    }
    if (files.length === 0) return;
    try {
      await window.electronAPI?.addPDFFiles(files);
    } catch (error) {
       toast.error("파일 업로드 중 오류 발생");
    }
  };

   const handleUploadClick = async () => {
    if (!isConnected) {
      toast.error('문서를 처리하려면 먼저 데이터베이스에 연결해주세요');
      return;
    }
    try {
      await window.electronAPI?.openPDFFiles();
    } catch (error) {
       toast.error("파일 열기 중 오류 발생");
    }
  };

  const handleDisconnect = async() => {
    try {
      const success = await window.electronAPI?.disconnectDB();
      setIsConnected(!success);
      if (success) {
        toast.info("데이터베이스 연결이 해제되었습니다.");
        const mockData = await window.electronAPI?.getInitialData();
        if (mockData) {
          setFolders(mockData.folders);
          setDocuments(mockData.documents);
          setSelectedIds([]);
        }
      } else {
        toast.error("데이터베이스 연결 해제에 실패했습니다.");
      }
    } catch (error) {
       toast.error("연결 해제 중 오류 발생");
    }
  };

  const handleConnectionChange = async (connectionConfig: any) => {
    try {
      const success = await window.electronAPI?.connectDB(connectionConfig);
      setIsConnected(success);
      if (success) {
        toast.success("데이터베이스에 성공적으로 연결되었습니다.");
        const dbData = await window.electronAPI?.getInitialData();
        if (dbData) {
          setFolders(dbData.folders);
          setDocuments(dbData.documents);
          setSelectedIds([]);
        }
      } else {
        toast.error("데이터베이스 연결에 실패했습니다.");
      }
    } catch (error) {
       toast.error("연결 중 오류 발생");
    }
  };

  const handleSelectDocument = useCallback((id: string, isMultiSelect: boolean) => {
    setSelectedIds(prev => {
      if (!isMultiSelect && prev.includes(id)) return prev;
      if (isMultiSelect) {
        return prev.includes(id) 
          ? prev.filter(itemId => itemId !== id) 
          : [...prev, id];
      } else {
        return [id];
      }
    });
  }, []);


  const handleSetSelectedIds = useCallback((ids: string[]) => {
    setSelectedIds(ids);
  }, []);

  const handleBulkDelete = async () => {
    if (selectedIds.length === 0) return;
    if (!confirm(`${selectedIds.length}개의 문서를 삭제하시겠습니까?`)) return;

    try {
      if (window.electronAPI.deleteDocuments) {
        await window.electronAPI.deleteDocuments(selectedIds);
      } else {
        for (const id of selectedIds) {
          const doc = documents.find(d => d.id === id);
          if (doc) await window.electronAPI.deleteDocument(id, doc.name);
        }
      }
      setDocuments(prev => prev.filter(doc => !selectedIds.includes(doc.id)));
      setSelectedIds([]);
      toast.success("선택한 문서가 삭제되었습니다.");
    } catch (error) {
      toast.error("문서 삭제 실패");
    }
  };

const handleDeleteFolder = async (folderId: string, folderName: string) => {
  if (!confirm(`"${folderName}" 폴더를 삭제하시겠습니까?\n(폴더 내 문서는 루트로 이동됩니다)`)) {
    return;
  }

  try {
    await window.electronAPI.deleteFolder(folderId);
    
    // UI 업데이트: 폴더 제거
    setFolders(prev => prev.filter(f => f.id !== folderId));
    
    // 삭제된 폴더에 속한 문서들을 루트로 이동
    setDocuments(prev => prev.map(doc => 
      doc.folderId === folderId ? { ...doc, folderId: undefined } : doc
    ));
    
    // 현재 선택된 폴더가 삭제된 경우 루트로 이동
    if (selectedFolder === folderId) {
      setSelectedFolder(null);
    }
    
    toast.success(`"${folderName}" 폴더가 삭제되었습니다`);
  } catch (error) {
    console.error('Folder delete error:', error);
    toast.error("폴더 삭제 실패");
  }
};

  const handleBulkMove = async (targetFolderId: string | null, draggedDocId?: string) => {
    let idsToMove = [...selectedIds];
    if (draggedDocId && !idsToMove.includes(draggedDocId)) {
      idsToMove = [draggedDocId];
    }
    if (idsToMove.length === 0) return;

    const folderName = targetFolderId ? (folders.find(f => f.id === targetFolderId)?.name ?? null) : null;

    try {
      if (window.electronAPI.moveDocuments) {
        await window.electronAPI.moveDocuments(idsToMove, folderName);
      } else {
        for (const id of idsToMove) {
          const doc = documents.find(d => d.id === id);
          if (doc) await window.electronAPI.moveToFolder(id, doc.name, folderName);
        }
      }
      setDocuments(prev => prev.map(doc => 
        idsToMove.includes(doc.id) ? { ...doc, folderId: targetFolderId || undefined } : doc
      ));
      setSelectedIds([]); 
      toast.success(`${idsToMove.length}개의 문서가 이동되었습니다.`);
    } catch (error) {
      toast.error("폴더 이동 실패");
    }
  };

  const handleDeleteDocument = async (id: string, name: string) => {
    try {
      await window.electronAPI?.deleteDocument(id, name);
      setDocuments(prev => prev.filter(doc => doc.id !== id));
      toast.success(`"${name}" 삭제됨`);
    } catch (error) {
      toast.error("문서 삭제 실패");
    }
  };

  const handleCreateFolder = async (name: string, color: string) => {
    try {
      const newFolder = await window.electronAPI?.createFolder(name, color);
      if (newFolder) {
        setFolders([...folders, newFolder]);
        toast.success(`"${name}" 폴더가 생성되었습니다`);
      } else {
        toast.error("중복 폴더입니다.");
      }
    } catch (error) {
      toast.error("폴더 생성 중 오류 발생");
    }
  };

  const handleMoveToFolder = async (documentId: string, documentName: string, folderId: string | null) => {
    const folderName: string | null = folderId ? (folders.find(f => f.id === folderId)?.name ?? null) : '루트';
    const targetFolderNameForApi = folderName === '루트' ? null : folderName;

    try {
      await window.electronAPI?.moveToFolder(documentId, documentName, targetFolderNameForApi);
      setDocuments(prev => prev.map(doc =>
        doc.id === documentId ? { ...doc, folderId: folderId || undefined } : doc
      ));
      toast.success(`문서가 "${folderName ?? '루트'}"(으)로 이동되었습니다`);
    } catch (error) {
      toast.error("폴더 이동 실패");
    }
  };

  // [추가] 문서 보기 핸들러
  const handleViewDocument = async (doc: PDFDocument) => {
    if (!isConnected) {
      toast.error("상세 내용을 보려면 데이터베이스에 연결되어 있어야 합니다.");
      return;
    }
    try {
      toast.loading("문서 내용을 불러오는 중...", { id: "loading-content" });
      const result = await window.electronAPI.getDocumentContent(doc.id);
      toast.dismiss("loading-content");
      
      if (result.success) {
        setViewingDoc(doc);
        setViewingContent({
          textChunks: result.textChunks || [],
          images: result.images || []
        });
        setIsViewerOpen(true);
      } else {
        toast.error(`불러오기 실패: ${result.error}`);
      }
    } catch (e) {
      toast.dismiss("loading-content");
      toast.error("문서 내용을 가져오는 중 오류가 발생했습니다.");
    }
  };

  const handleDownloadDocument = async (doc: PDFDocument) => {
     if (!isConnected) {
      toast.error("다운로드하려면 데이터베이스에 연결되어 있어야 합니다.");
      return;
    }
    try {
      toast.info("다운로드 시작...");
      const result = await window.electronAPI.downloadDocument(doc.id, doc.name);
      if (result.success) {
        toast.success(`다운로드 완료: ${result.filePath}`);
      } else if (result.message !== 'Canceled') {
        toast.error("다운로드 실패");
      }
    } catch (e) {
      toast.error("다운로드 중 오류 발생");
    }
  };

  const handleDeleteChunk = async (chunkId: string) => {
    try {
      const result = await window.electronAPI.deleteTextChunk(chunkId);
      if (result.success) {
        // 성공 시 뷰잉 컨텐츠 상태 업데이트 (UI 즉시 반영)
        setViewingContent(prev => ({
          ...prev,
          textChunks: prev.textChunks.filter(c => c.id !== chunkId)
        }));
        toast.success("텍스트 청크가 삭제되었습니다.");
      } else {
        toast.error("삭제 실패");
      }
    } catch (e) {
      console.error(e);
      toast.error("삭제 중 오류 발생");
    }
  };

  const handleDeleteImage = async (imageId: string) => {
    try {
      const result = await window.electronAPI.deleteImage(imageId);
      if (result.success) {
        // 성공 시 뷰잉 컨텐츠 상태 업데이트 (UI 즉시 반영)
        setViewingContent(prev => ({
          ...prev,
          images: prev.images.filter(c => c.id !== imageId)
        }));
        toast.success("이미지가 삭제되었습니다.");
      } else {
        toast.error("삭제 실패");
      }
    } catch (e) {
      console.error(e);
      toast.error("삭제 중 오류 발생");
    }
  };

  const handleSaveTextChunk = async (chunkId: string, newContent: string) => {
    try {
      const result = await window.electronAPI.updateTextChunk(chunkId, newContent);
      if (result.success) {
        toast.success("수정되었습니다.");
      } else {
        toast.error("수정 실패");
      }
    } catch (e) {
      console.error(e);
      toast.error("저장 중 오류 발생");
    }
  };

  // 검색 및 정렬
  const filteredByFolder = selectedFolder
    ? documents.filter(doc => doc.folderId === selectedFolder)
    : documents;

  const searchedDocuments = filteredByFolder.filter(doc => {
    const normalizedName = (doc.name || '').normalize('NFC').toLowerCase();
    const normalizedQuery = searchQuery.normalize('NFC').toLowerCase();
    return normalizedName.startsWith(normalizedQuery);
  });

  const sortedDocuments = [...searchedDocuments].sort((a, b) => {
    const dateA = a.uploadDate instanceof Date ? a.uploadDate.getTime() : 0;
    const dateB = b.uploadDate instanceof Date ? b.uploadDate.getTime() : 0;

    switch (sortBy) {
      case 'name': return a.name.localeCompare(b.name);
      case 'date': return dateB - dateA;
      case 'status':
        const statusOrder = { ready: 0, processing: 1, error: 2 };
        return statusOrder[a.status] - statusOrder[b.status];
      case 'size': return b.size - a.size;
      default: return 0;
    }
  });

  return (
    <SidebarProvider>
      <div className="flex min-h-screen w-full">
        <AppSidebar
          activeSection={activeSection}
          onSectionChange={setActiveSection}
          isConnected={isConnected}
          documentCount={documents.length}
          folders={folders}
          selectedFolder={selectedFolder}
          onSelectFolder={setSelectedFolder}
          onDropDocuments={handleBulkMove}
          onDeleteFolder={handleDeleteFolder} 
        />

        <main className="flex-1 bg-neutral-50">
          <header className="border-b bg-gradient-to-r from-white to-blue-50 px-6 py-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="flex items-center gap-3">
                  <h1>
                    {activeSection === 'documents' && '문서 관리'}
                    {activeSection === 'upload' && '문서 업로드'}
                    {activeSection === 'database' && '데이터베이스 연결'}
                  </h1>
                  {activeSection === 'documents' && (
                    <div className="flex items-center gap-2">
                      <Badge variant="secondary" className="bg-blue-100 text-blue-700 border-blue-200">
                        전체 {documents.length}개
                      </Badge>
                      {selectedIds.length > 0 && (
                        <Badge variant="secondary" className="animate-in fade-in bg-green-200 text-green-700 border-green-200">
                          {selectedIds.length}개 선택됨
                        </Badge>
                      )}
                    </div>
                  )}
                </div>
                <p className="text-neutral-600 mt-1">
                  {activeSection === 'documents' && 'PDF 문서를 관리합니다'}
                  {activeSection === 'upload' && 'PDF 문서를 로컬에서 업로드하고 처리합니다'}
                  {activeSection === 'database' && '데이터베이스 연결 설정을 구성합니다'}
                </p>
              </div>

              {activeSection === 'documents' && (
                <div className="flex items-center gap-2">
                  {selectedIds.length > 0 && (
                    <div className="flex items-center mr-2 pr-2 border-r border-gray-300 gap-2 animate-in slide-in-from-top-2">
                       <Button 
                        variant="destructive" 
                        size="sm" 
                        onClick={handleBulkDelete}
                        className="gap-2"
                      >
                        <Trash2 className="w-4 h-4" />
                        삭제 ({selectedIds.length})
                      </Button>
                      <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={() => setSelectedIds([])}
                      >
                        취소
                      </Button>
                    </div>
                  )}
                  <Select value={sortBy} onValueChange={(value: any) => setSortBy(value)}>
                    <SelectTrigger className="w-[140px] h-9">
                      <ArrowUpDown className="w-4 h-4 mr-2" />
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="date">날짜순</SelectItem>
                      <SelectItem value="name">이름순</SelectItem>
                      <SelectItem value="status">상태순</SelectItem>
                      <SelectItem value="size">크기순</SelectItem>
                    </SelectContent>
                  </Select>

                  {viewMode === 'grid' && (
                    <div className="flex items-center gap-1 border rounded-md p-1">
                      <Button variant={gridSize === 'small' ? 'default' : 'ghost'} size="sm" className="h-7 px-2" onClick={() => setGridSize('small')}>
                        <Minimize2 className="w-3 h-3" />
                      </Button>
                      <Button variant={gridSize === 'medium' ? 'default' : 'ghost'} size="sm" className="h-7 px-2" onClick={() => setGridSize('medium')}>
                        <LayoutGrid className="w-3 h-3" />
                      </Button>
                      <Button variant={gridSize === 'large' ? 'default' : 'ghost'} size="sm" className="h-7 px-2" onClick={() => setGridSize('large')}>
                        <Maximize2 className="w-3 h-3" />
                      </Button>
                    </div>
                  )}

                  <Button variant="outline" size="sm" onClick={() => setIsFolderDialogOpen(true)}>
                    <FolderPlus className="w-4 h-4 mr-2" />
                    새 폴더
                  </Button>
                  <Button variant={viewMode === 'grid' ? 'default' : 'outline'} size="sm" onClick={() => setViewMode('grid')}>
                    <LayoutGrid className="w-4 h-4" />
                  </Button>
                  <Button variant={viewMode === 'table' ? 'default' : 'outline'} size="sm" onClick={() => setViewMode('table')}>
                    <Table className="w-4 h-4" />
                  </Button>
                </div>
              )}
            </div>
          </header>
          <div className="p-6">  
            {activeSection === 'documents' && (
              <div className="relative w-64 mb-4">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-neutral-500" />
                <Input
                  type="search"
                  placeholder=" 문서 검색..."
                  className="w-full pl-9 h-9"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            )}
            {activeSection === 'documents' && (
              <>
                {viewMode === 'grid' ? (
                  <DocumentGrid
                    documents={sortedDocuments}
                    folders={folders}
                    onDelete={handleDeleteDocument}
                    onMoveToFolder={handleMoveToFolder}
                    isConnected={isConnected}
                    gridSize={gridSize}
                    selectedIds={selectedIds}
                    onSelectDocument={handleSelectDocument}
                    onSetSelectedIds={handleSetSelectedIds}
                    onView={handleViewDocument}
                    onDownload={handleDownloadDocument}
                  />
                ) : (
                  <DocumentTable
                    documents={sortedDocuments}
                    folders={folders}
                    onDelete={handleDeleteDocument}
                    onMoveToFolder={handleMoveToFolder}
                    isConnected={isConnected}
                    selectedIds={selectedIds}
                    onSelectDocument={handleSelectDocument}
                    onView={handleViewDocument}
                    onDownload={handleDownloadDocument}
                  />
                )}
              </>
            )}
            {activeSection === 'upload' && (
              <PDFUploadZone onUpload={handleUploadDrop} onClick={handleUploadClick} isConnected={isConnected} />
            )}
            {activeSection === 'database' && (
              <DatabaseConnection
                isConnected={isConnected}
                onConnectionChange={handleConnectionChange}
                onDisconnect={handleDisconnect}
              />
            )}
          </div>
        </main>
      </div>

      <FolderDialog
        open={isFolderDialogOpen}
        onOpenChange={setIsFolderDialogOpen}
        onCreateFolder={handleCreateFolder}
      />

      {/* 뷰어 모달 */}
      {viewingDoc && (
        <DocumentViewer
          isOpen={isViewerOpen}
          onClose={() => setIsViewerOpen(false)}
          title={viewingDoc.name}
          textChunks={viewingContent.textChunks}
          images={viewingContent.images}
          onDownloadPdf={() => handleDownloadDocument(viewingDoc)}
          onSaveTextChunk={handleSaveTextChunk}
          onDeleteTextChunk={handleDeleteChunk}
          onDeleteImage ={handleDeleteImage}
        />
      )}

      <Toaster />
    </SidebarProvider>
  );
}
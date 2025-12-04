import { MoreVertical, Download, Trash2, Eye, FolderInput, Database } from 'lucide-react';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
} from './ui/dropdown-menu';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from './ui/table';
import { Checkbox } from './ui/checkbox';
import { cn } from '../lib/utils'; 

import { toast } from 'sonner';

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
  // dbUploaded 제거됨
}

interface DocumentTableProps {
  documents: PDFDocument[];
  folders: Folder[];
  onDelete: (id: string, name: string) => void;
  onMoveToFolder: (documentId: string, documentName:string, folderId: string | null) => void;
  isConnected: boolean;
  selectedIds: string[];
  onSelectDocument: (id: string, isMultiSelect: boolean) => void;
  
  // [추가] 보기 및 다운로드 핸들러
  onView: (doc: PDFDocument) => void;
  onDownload: (doc: PDFDocument) => void;
}

export function DocumentTable({ 
  documents, 
  folders,
  onDelete, 
  onMoveToFolder,
  isConnected,
  selectedIds,
  onSelectDocument,
  onView,
  onDownload
}: DocumentTableProps) {
  
  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDate = (date: Date) => {
    return new Intl.DateTimeFormat('ko-KR', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  };

  const handleDelete = (id: string, name: string) => {
    onDelete(id, name);
  };

  const handleAction = (action: string, name: string) => {
    toast.info(`${action} "${name}"`);
  };

  const allVisibleDocIds = documents.map(doc => doc.id);
  const allVisibleSelected = allVisibleDocIds.length > 0 && allVisibleDocIds.every(id => selectedIds.includes(id));
  const someVisibleSelected = allVisibleDocIds.some(id => selectedIds.includes(id));

  const handleSelectAllClick = (checked: boolean | 'indeterminate') => {
    if (checked) {
      allVisibleDocIds.forEach(id => {
        if (!selectedIds.includes(id)) {
          onSelectDocument(id, true); 
        }
      });
    } else {
      allVisibleDocIds.forEach(id => {
        if (selectedIds.includes(id)) {
          onSelectDocument(id, true); 
        }
      });
    }
  };

  return (
    <div className="rounded-lg border bg-white">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[40px] px-4">
              <Checkbox 
                checked={allVisibleSelected ? true : someVisibleSelected ? 'indeterminate' : false}
                onCheckedChange={(checked) => handleSelectAllClick(checked)}
              />
            </TableHead>
            <TableHead>이름</TableHead>
            <TableHead>상태</TableHead>
            <TableHead>폴더</TableHead>
            <TableHead>크기</TableHead>
            <TableHead>업로드 날짜</TableHead>
            <TableHead className="text-right">작업</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {documents.map((doc) => {
            const folder = doc.folderId ? folders.find(f => f.id === doc.folderId) : null;
            const isSelected = selectedIds.includes(doc.id);
            
            return (
              <TableRow 
                key={doc.id} 
                data-state={isSelected ? 'selected' : 'unselected'}
                className={cn(
                  "hover:bg-blue-50/50 transition-colors data-[state=selected]:bg-blue-100",
                  "cursor-pointer"
                )}
                onClick={(e) => onSelectDocument(doc.id, true)}
                draggable={true}
                onDragStart={(e) => {
                  e.stopPropagation();
    
                  e.dataTransfer.setData('text/plain', doc.id);
                  e.dataTransfer.effectAllowed = 'move';
                }}
              >
                <TableCell 
                  className="px-4"
                  onClick={(e) => e.stopPropagation()} 
                >
                  <Checkbox 
                    checked={isSelected}
                    onCheckedChange={() => onSelectDocument(doc.id, true)} 
                  />
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-3">
                    <div className="flex h-8 w-8 items-center justify-center rounded bg-gradient-to-br from-red-100 to-red-200">
                      <span className="text-red-600">PDF</span>
                    </div>
                    <span>{doc.name}</span>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge 
                    variant={
                      doc.status === 'ready' ? 'default' : 
                      doc.status === 'processing' ? 'secondary' : 
                      'destructive'
                    }
                  >
                    {doc.status === 'ready' ? '완료' : 
                     doc.status === 'processing' ? '처리중' : '오류'}
                  </Badge>
                </TableCell>
                <TableCell>
                  {folder ? (
                    <div className="flex items-center gap-1">
                      <FolderInput className="h-4 w-4 text-neutral-500" />
                      <span>{folder.name}</span>
                    </div>
                  ) : (
                    <span className="text-neutral-400">루트</span>
                  )}
                </TableCell>
                <TableCell>{formatFileSize(doc.size)}</TableCell>
                <TableCell>{formatDate(doc.uploadDate)}</TableCell>
                <TableCell 
                  className="text-right"
                  onClick={(e) => e.stopPropagation()}
                >
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="sm">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      {/*  보기 핸들러 연결 */}
                      <DropdownMenuItem onClick={() => onView(doc)}>
                        <Eye className="h-4 w-4 mr-2" />
                        보기
                      </DropdownMenuItem>
                      {/*다운로드 핸들러 연결 */}
                      <DropdownMenuItem onClick={() => onDownload(doc)}>
                        <Download className="h-4 w-4 mr-2" />
                        다운로드
                      </DropdownMenuItem>
                      
                      {doc.status === 'ready' && (
                        <DropdownMenuSub>
                          <DropdownMenuSubTrigger>
                            <FolderInput className="h-4 w-4 mr-2" />
                            폴더로 이동
                          </DropdownMenuSubTrigger>
                          <DropdownMenuSubContent>
                            <DropdownMenuItem onClick={() => onMoveToFolder(doc.id, doc.name, null)}>
                              루트
                            </DropdownMenuItem>
                            {folders.map((folder) => (
                              <DropdownMenuItem 
                                key={folder.id}
                                onClick={() => onMoveToFolder(doc.id, doc.name, folder.id)}
                              >
                                {folder.name}
                              </DropdownMenuItem>
                            ))}
                          </DropdownMenuSubContent>
                        </DropdownMenuSub>
                      )}
                      
                      <DropdownMenuSeparator />
                      <DropdownMenuItem 
                        className="text-red-600"
                        onClick={() => handleDelete(doc.id, doc.name)}
                      >
                        <Trash2 className="h-4 w-4 mr-2" />
                        {'삭제'}
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
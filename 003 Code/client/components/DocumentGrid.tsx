import { useState, useRef, useCallback } from 'react';
import { FileText, MoreVertical, Download, Trash2, Eye, FolderInput, Database } from 'lucide-react';
import { Card } from './ui/card';
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
}

interface DocumentGridProps {
  documents: PDFDocument[];
  folders: Folder[];
  onDelete: (id: string, name: string) => void;
  onMoveToFolder: (documentId: string, documentName:string, folderId: string | null) => void;
  isConnected: boolean;
  gridSize: 'small' | 'medium' | 'large';
  selectedIds: string[];
  onSelectDocument: (id: string, isMultiSelect: boolean) => void;
  onSetSelectedIds: (ids: string[]) => void;
  onView: (doc: PDFDocument) => void;
  onDownload: (doc: PDFDocument) => void;
}

export function DocumentGrid({ 
  documents, 
  folders,
  onDelete, 
  onMoveToFolder,
  isConnected,
  gridSize,
  selectedIds,
  onSelectDocument,
  onSetSelectedIds,
  onView,
  onDownload
}: DocumentGridProps) {
  
  const [isMarqueeDragging, setIsMarqueeDragging] = useState(false);
  const [marqueeRect, setMarqueeRect] = useState<{ x: number, y: number, width: number, height: number } | null>(null);
  const [dragStartPoint, setDragStartPoint] = useState<{ x: number, y: number } | null>(null);

  const gridRef = useRef<HTMLDivElement>(null); 
  const cardRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  const getGridCols = () => {
    switch (gridSize) {
      case 'small':
        return 'grid-cols-2 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8';
      case 'medium':
        return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4';
      case 'large':
        return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3';
      default:
        return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4';
    }
  };

  const getCardPadding = () => {
    switch (gridSize) {
      case 'small':
        return 'p-3';
      case 'medium':
        return 'p-4';
      case 'large':
        return 'p-5';
      default:
        return 'p-4';
    }
  };

  const getIconSize = () => {
    switch (gridSize) {
      case 'small':
        return { container: 'h-8 w-8', icon: 'h-4 w-4', badge: 'h-4 w-4', badgeIcon: 'h-2 w-2' };
      case 'medium':
        return { container: 'h-12 w-12', icon: 'h-6 w-6', badge: 'h-5 w-5', badgeIcon: 'h-3 w-3' };
      case 'large':
        return { container: 'h-16 w-16', icon: 'h-8 w-8', badge: 'h-6 w-6', badgeIcon: 'h-3.5 w-3.5' };
      default:
        return { container: 'h-12 w-12', icon: 'h-6 w-6', badge: 'h-5 w-5', badgeIcon: 'h-3 w-3' };
    }
  };

  const iconSizes = getIconSize();
  
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
      year: 'numeric'
    }).format(date);
  };

  const handleDelete = (id: string, name: string) => {
    onDelete(id, name);
  };

  const handleAction = (action: string, name: string) => {
    toast.info(`${action} "${name}"`);
  };

  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    e.preventDefault(); 
    e.stopPropagation();

    setIsMarqueeDragging(true);

    const gridRect = gridRef.current?.getBoundingClientRect();
    if (!gridRect) return;

    const startX = e.clientX - gridRect.left;
    const startY = e.clientY - gridRect.top;

    setDragStartPoint({ x: startX, y: startY });
    setMarqueeRect({ x: startX, y: startY, width: 0, height: 0 });

    if (!e.metaKey && !e.ctrlKey) {
      onSetSelectedIds([]);
    }
  }, [onSetSelectedIds]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!isMarqueeDragging || !dragStartPoint || !gridRef.current) return;

    e.preventDefault();
    e.stopPropagation();

    const gridRect = gridRef.current.getBoundingClientRect();
    const currentX = e.clientX - gridRect.left;
    const currentY = e.clientY - gridRect.top;

    const x = Math.min(dragStartPoint.x, currentX);
    const y = Math.min(dragStartPoint.y, currentY);
    const width = Math.abs(currentX - dragStartPoint.x);
    const height = Math.abs(currentY - dragStartPoint.y);

    const newMarqueeRect = { x, y, width, height };
    setMarqueeRect(newMarqueeRect);

    const newSelectedIds: string[] = [];
    const marqueeRight = newMarqueeRect.x + newMarqueeRect.width;
    const marqueeBottom = newMarqueeRect.y + newMarqueeRect.height;

    cardRefs.current.forEach((cardEl, id) => {
      const cardRect = {
        top: cardEl.offsetTop,
        left: cardEl.offsetLeft,
        right: cardEl.offsetLeft + cardEl.offsetWidth,
        bottom: cardEl.offsetTop + cardEl.offsetHeight,
      };

      const isIntersecting =
        cardRect.left < marqueeRight &&
        cardRect.right > newMarqueeRect.x &&
        cardRect.top < marqueeBottom &&
        cardRect.bottom > newMarqueeRect.y;

      if (isIntersecting) {
        newSelectedIds.push(id);
      }
    });

    onSetSelectedIds(newSelectedIds);

  }, [isMarqueeDragging, dragStartPoint, onSetSelectedIds]);

  const handleMouseUp = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    setIsMarqueeDragging(false);
    setMarqueeRect(null);
    setDragStartPoint(null);
  }, []);

  if (documents.length === 0) {
    return (
      <div 
        ref={gridRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        className="flex flex-col items-center justify-center py-16 text-center w-full h-full relative"
      >
        <div className="flex h-20 w-20 items-center justify-center rounded-full bg-neutral-100 mb-4 pointer-events-none">
          <FileText className="h-10 w-10 text-neutral-400" />
        </div>
        <h3 className="pointer-events-none">문서가 없습니다</h3>
        <p className="text-neutral-600 mt-2 pointer-events-none">
          첫 번째 PDF 문서를 업로드하여 시작하세요
        </p>

        {isMarqueeDragging && marqueeRect && (
          <div
            className="absolute border border-blue-500 bg-blue-500/20 pointer-events-none"
            style={{
              left: marqueeRect.x,
              top: marqueeRect.y,
              width: marqueeRect.width,
              height: marqueeRect.height,
            }}
          />
        )}
      </div>
    );
  }

  return (
    <div 
      ref={gridRef}
      className={cn(
        `grid ${getGridCols()} gap-4`,
        "relative",
        "w-full h-full overflow-auto content-start p-4"
      )}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
    >
      {documents.map((doc) => {
        const folder = doc.folderId ? folders.find(f => f.id === doc.folderId) : null;
        const isSelected = selectedIds.includes(doc.id);
        
        return (
          <Card 
            key={doc.id}
            ref={(node) => {
              const map = cardRefs.current;
              if (node) {
                map.set(doc.id, node);
              } else {
                map.delete(doc.id);
              }
            }}
            data-state={isSelected ? 'selected' : 'unselected'}
            className={cn(
              "overflow-hidden hover:shadow-lg hover:border-blue-200 transition-all group cursor-pointer",
              "z-10",
              isSelected && "ring-2 ring-blue-500 border-blue-500 bg-blue-50"
            )}
            onMouseDown={(e) => {
              e.stopPropagation(); 
              
              const isSelected = selectedIds.includes(doc.id);
              const isMultiKey = e.metaKey || e.ctrlKey;

              if (isSelected && !isMultiKey) {
                return;
              }
              
              onSelectDocument(doc.id, isMultiKey);
            }}
            draggable={true}
            onDragStart={(e) => {
              e.stopPropagation(); 
              e.dataTransfer.setData('text/plain', doc.id);
            }}
          >
            <div className={getCardPadding()}>
              <div className={`flex items-start justify-between ${gridSize === 'small' ? 'mb-2' : 'mb-3'}`}>
                <div className={`flex ${iconSizes.container} items-center justify-center rounded-lg bg-gradient-to-br from-red-100 to-red-200 relative group-hover:from-red-200 group-hover:to-red-300 transition-all`}>
                  <FileText className={`${iconSizes.icon} text-red-600`} />
                </div>
                
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onMouseDown={(e) => e.stopPropagation()}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => onView(doc)}>
                      <Eye className="h-4 w-4 mr-2" />
                      보기
                    </DropdownMenuItem>
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
                          <DropdownMenuItem onClick={() => onMoveToFolder(doc.id,doc.name,null)}>
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
              </div>

              <div className={gridSize === 'small' ? 'space-y-1' : 'space-y-2'}>
                <h4 className={`truncate ${gridSize === 'small' ? 'text-sm' : ''}`} title={doc.name}>
                  {doc.name}
                </h4>
                
                {gridSize !== 'small' && (
                  <>
                    <div className="flex items-center gap-2 flex-wrap">
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
                    </div>

                    {folder && (
                      <div className="flex items-center gap-1 text-neutral-600">
                        <FolderInput className="h-3 w-3" />
                        <span>{folder.name}</span>
                      </div>
                    )}

                    <div className="text-neutral-600">
                      <p>{formatFileSize(doc.size)}</p>
                      <p>{formatDate(doc.uploadDate)}</p>
                    </div>

                    {doc.tags && doc.tags.length > 0 && gridSize === 'large' && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {doc.tags.map((tag, index) => (
                          <Badge key={index} variant="outline">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </>
                )}

                {gridSize === 'small' && (
                  <div className="flex items-center gap-1">
                    <Badge 
                      variant={
                        doc.status === 'ready' ? 'default' : 
                        doc.status === 'processing' ? 'secondary' : 
                        'destructive'
                      }
                      className="text-xs h-5"
                    >
                      {doc.status === 'ready' ? '완료' : 
                       doc.status === 'processing' ? '처리중' : '오류'}
                    </Badge>
                  </div>
                )}
              </div>
            </div>
          </Card>
        );
      })}

      {isMarqueeDragging && marqueeRect && (
        <div
          className="absolute border border-blue-500 bg-blue-500/20 pointer-events-none"
          style={{
            left: marqueeRect.x,
            top: marqueeRect.y,
            width: marqueeRect.width,
            height: marqueeRect.height,
          }}
        />
      )}
    </div>
  );
}
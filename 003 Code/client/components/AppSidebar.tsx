import { useState } from 'react';
import { Database, FileText, Upload, Settings, Folder, FolderOpen, Trash2, MoreVertical } from 'lucide-react';
import {
  Sidebar,
  SidebarContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
} from './ui/sidebar';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import { cn } from '../lib/utils';

export interface Folder {
  id: string;
  name: string;
  color: string;
  createdDate: Date;
}

interface AppSidebarProps {
  activeSection: 'documents' | 'upload' | 'database';
  onSectionChange: (section: 'documents' | 'upload' | 'database') => void;
  isConnected: boolean;
  documentCount: number;
  folders: Folder[];
  selectedFolder: string | null;
  onSelectFolder: (folderId: string | null) => void;
  onDropDocuments?: (targetFolderId: string | null, draggedDocId?: string) => void;
  onDeleteFolder?: (folderId: string, folderName: string) => void;
}

const getFolderColor = (color: string) => {
  const colors: Record<string, string> = {
    blue: 'text-blue-500',
    green: 'text-green-500',
    purple: 'text-purple-500',
    orange: 'text-orange-500',
    pink: 'text-pink-500',
    red: 'text-red-500',
  };
  return colors[color] || 'text-blue-500';
};

export function AppSidebar({ 
  activeSection, 
  onSectionChange, 
  isConnected,
  documentCount,
  folders,
  selectedFolder,
  onSelectFolder,
  onDropDocuments,
  onDeleteFolder
}: AppSidebarProps) {
  
  const [dragOverFolderId, setDragOverFolderId] = useState<string | null | 'root'>(null);

  const handleDragOver = (e: React.DragEvent, folderId: string | null) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOverFolderId(folderId === null ? 'root' : folderId);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOverFolderId(null);
  };

  const handleDrop = (e: React.DragEvent, targetFolderId: string | null) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOverFolderId(null);

    const draggedDocId = e.dataTransfer.getData('text/plain');
    
    if (onDropDocuments) {
      onDropDocuments(targetFolderId, draggedDocId);
    }
  };

  const handleDeleteFolder = (e: React.MouseEvent, folderId: string, folderName: string) => {
    e.stopPropagation();
    
    if (onDeleteFolder) {
      onDeleteFolder(folderId, folderName);
    }
  };

  return (
    <Sidebar>
      <SidebarHeader className="border-b px-6 py-4 bg-gradient-to-br from-blue-100 to-indigo-100">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-white shadow-sm">
            <FileText className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <h2 className="text-blue-900">CustomRAG</h2>
            <p className="text-blue-700">Database</p>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent className="px-3 py-4">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              isActive={activeSection === 'documents'}
              onClick={() => onSectionChange('documents')}
              className="w-full"
            >
              <FileText className="h-4 w-4" />
              <span>문서</span>
              <Badge variant="secondary" className="ml-auto">
                {documentCount}
              </Badge>
            </SidebarMenuButton>
          </SidebarMenuItem>

          <SidebarMenuItem>
            <SidebarMenuButton
              isActive={activeSection === 'upload'}
              onClick={() => onSectionChange('upload')}
              className="w-full"
            >
              <Upload className="h-4 w-4" />
              <span>업로드</span>
            </SidebarMenuButton>
          </SidebarMenuItem>

          <SidebarMenuItem>
            <SidebarMenuButton
              isActive={activeSection === 'database'}
              onClick={() => onSectionChange('database')}
              className="w-full"
            >
              <Database className="h-4 w-4" />
              <span>데이터베이스</span>
              <div className="ml-auto">
                <div className={`h-2 w-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-neutral-300'}`} />
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>

        {activeSection === 'documents' && (
          <SidebarGroup className="mt-4">
            <SidebarGroupLabel>폴더</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {/* 전체 문서 (루트) */}
                <SidebarMenuItem>
                  <SidebarMenuButton
                    isActive={selectedFolder === null}
                    onClick={() => onSelectFolder(null)}
                    onDragOver={(e) => handleDragOver(e, null)}
                    onDragLeave={handleDragLeave}
                    onDrop={(e) => handleDrop(e, null)}
                    className={`w-full transition-colors duration-200 ${
                      dragOverFolderId === 'root' ? 'bg-blue-100 ring-2 ring-inset ring-blue-300' : ''
                    }`}
                  >
                    <FolderOpen className="h-4 w-4" />
                    <span>전체 문서</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                
                {/* 개별 폴더들 */}
                {folders.map((folder) => (
                  <SidebarMenuItem key={folder.id}>
                    <div className="relative group w-full">
                      <SidebarMenuButton
                        isActive={selectedFolder === folder.id}
                        onClick={() => onSelectFolder(folder.id)}
                        onDragOver={(e) => handleDragOver(e, folder.id)}
                        onDragLeave={handleDragLeave}
                        onDrop={(e) => handleDrop(e, folder.id)}
                        className={`w-full transition-colors duration-200 pr-8 ${
                          dragOverFolderId === folder.id ? 'bg-blue-100 ring-2 ring-inset ring-blue-300' : ''
                        }`}
                      >
                        <Folder className={`h-4 w-4 ${getFolderColor(folder.color)}`} />
                        <span>{folder.name}</span>
                      </SidebarMenuButton>
                      
                      {/* 삭제 버튼 */}
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <MoreVertical className="h-3 w-3" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            className="text-red-600"
                            onClick={(e) => handleDeleteFolder(e, folder.id, folder.name)}
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            삭제
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>

      <SidebarFooter className="border-t px-3 py-4">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton className="w-full">
              <Settings className="h-4 w-4" />
              <span>설정</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
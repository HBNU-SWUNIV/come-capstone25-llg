import { useState } from 'react';
import { Button } from './ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Input } from './ui/input';
import { Label } from './ui/label';

interface FolderDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreateFolder: (name: string, color: string) => void;
}

const FOLDER_COLORS = [
  { value: 'blue', label: '파란색', color: 'bg-blue-500' },
  { value: 'green', label: '초록색', color: 'bg-green-500' },
  { value: 'purple', label: '보라색', color: 'bg-purple-500' },
  { value: 'orange', label: '주황색', color: 'bg-orange-500' },
  { value: 'pink', label: '분홍색', color: 'bg-pink-500' },
  { value: 'red', label: '빨간색', color: 'bg-red-500' },
];

export function FolderDialog({ open, onOpenChange, onCreateFolder }: FolderDialogProps) {
  const [name, setName] = useState('');
  const [color, setColor] = useState('blue');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (name.trim()) {
      onCreateFolder(name.trim(), color);
      setName('');
      setColor('blue');
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>새 폴더 만들기</DialogTitle>
          <DialogDescription>
            문서를 정리할 새 폴더를 만듭니다
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit}>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="folder-name">폴더 이름</Label>
              <Input
                id="folder-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="폴더 이름을 입력하세요"
                autoFocus
              />
            </div>

            <div className="space-y-2">
              <Label>폴더 색상</Label>
              <div className="flex gap-2">
                {FOLDER_COLORS.map((colorOption) => (
                  <button
                    key={colorOption.value}
                    type="button"
                    onClick={() => setColor(colorOption.value)}
                    className={`h-8 w-8 rounded-full ${colorOption.color} transition-transform ${
                      color === colorOption.value ? 'ring-2 ring-neutral-900 ring-offset-2 scale-110' : ''
                    }`}
                    title={colorOption.label}
                  />
                ))}
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              취소
            </Button>
            <Button type="submit" disabled={!name.trim()}>
              생성
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

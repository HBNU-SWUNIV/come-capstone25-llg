import { useCallback, useState } from 'react';
import { Upload, FileText, Database } from 'lucide-react';
import { Card } from './ui/card';
import { Button } from './ui/button';
import { toast } from 'sonner';

// 1. onUpload가 받을 데이터의 타입을 정의합니다. (중요)
interface DroppedFileData {
  name: string;
  buffer: ArrayBuffer;
}

interface PDFUploadZoneProps {
  // 2. onUpload 타입을 새 인터페이스 배열로 변경
  onUpload: (files: DroppedFileData[]) => void;
  onClick: () => void;
  isConnected: boolean;
}

// 3. File 객체를 ArrayBuffer로 읽는 헬퍼 함수 (중요)
const readFileAsArrayBuffer = (file: File): Promise<DroppedFileData> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      resolve({
        name: file.name,
        buffer: reader.result as ArrayBuffer,
      });
    };
    reader.onerror = (error) => {
      reject(error);
    };
    reader.readAsArrayBuffer(file);
  });
};


export function PDFUploadZone({ onUpload, onClick, isConnected }: PDFUploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  // 4. handleDrop 로직 (ArrayBuffer 추출 방식으로 변경 - 중요)
  const handleDrop = useCallback(async (e: React.DragEvent) => { // 👈 async 추가
    e.preventDefault();
    setIsDragging(false);

    if (!isConnected) {
      toast.error('먼저 데이터베이스에 연결해주세요');
      return;
    }

    const files = e.dataTransfer.files; // FileList 사용
    
    if (!files || files.length === 0) {
      return;
    }

    const pdfFiles: File[] = [];
    let nonPdfsFound = false;

    for (const file of Array.from(files)) {
      // 5. file.name으로 PDF 검사 (경로 접근 X)
      if (file.name.toLowerCase().endsWith('.pdf')) {
        pdfFiles.push(file);
      } else {
        nonPdfsFound = true;
      }
    }

    if (pdfFiles.length === 0) {
      toast.error('PDF 파일만 업로드할 수 있습니다');
      return;
    }

    if (nonPdfsFound) {
      toast.info('PDF 파일이 아닌 파일은 제외되었습니다.');
    }

    try {
      toast.info('파일을 읽는 중입니다...');
      // 6. 모든 파일을 ArrayBuffer로 읽을 때까지 기다립니다. (핵심 로직)
      const fileDataArray = await Promise.all(
        pdfFiles.map(file => readFileAsArrayBuffer(file))
      );
      
      // 7. {이름, 버퍼} 객체 배열을 onUpload로 전달
      onUpload(fileDataArray);

    } catch (error) {
      console.error("파일 읽기 오류:", error);
      toast.error("파일을 읽는 중 오류가 발생했습니다.");
    }

  }, [onUpload, isConnected]);


  return (
    <div className="max-w-4xl mx-auto">
      {/* ----- 데이터베이스 연결 필요 카드 (변경 없음) ----- */}
      {!isConnected && (
        <Card className="p-4 mb-6 border-orange-300 bg-gradient-to-r from-orange-50 to-orange-100">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-orange-400 to-orange-500 shadow-md">
              <Database className="h-5 w-5 text-white" />
            </div>
            <div>
              <h4 className="text-orange-900">데이터베이스 연결 필요</h4>
              <p className="text-orange-700 mt-1">
                문서를 처리하려면 먼저 데이터베이스 섹션에서 연결해주세요
              </p>
            </div>
          </div>
        </Card>
      )}
      
      {/* ----- 드롭존 카드 (변경 없음) ----- */}
      <Card
        className={`border-2 border-dashed p-12 text-center transition-colors ${
          !isConnected 
            ? 'border-neutral-200 bg-neutral-50 opacity-60 cursor-not-allowed'
            : isDragging 
              ? 'border-neutral-900 bg-neutral-50' 
              : 'border-neutral-300 bg-white hover:border-neutral-400'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="flex flex-col items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-neutral-100">
            <Upload className="h-8 w-8 text-neutral-600" />
          </div>
          
          <div>
            <h3>PDF 문서 업로드</h3>
            <p className="text-neutral-600 mt-2">
              PDF 파일을 여기에 드래그 앤 드롭하거나 클릭하여 선택하세요
            </p>
          </div>

          <Button 
            onClick={onClick} 
            disabled={!isConnected}
          >
            <FileText className="w-4 h-4 mr-2" />
            파일 선택
          </Button>

          <div className="mt-4 text-neutral-500">
            <p>최대 파일 크기: 파일당 50MB</p>
            <p>지원 형식: PDF</p>
          </div>
        </div>
      </Card>

      {/* ----- 하단 3개 정보 카드 (변경 없음) ----- */}
      <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-6 border-blue-200 hover:border-blue-300 hover:shadow-md transition-all">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 shadow-sm">
              <Upload className="h-5 w-5 text-white" />
            </div>
            <div>
              <h4 className="text-blue-900">로컬 처리</h4>
              <p className="text-neutral-600 mt-1">
                모든 PDF 파일은 최대 보안을 위해 PC에서 로컬로 처리됩니다
              </p>
            </div>
          </div>
        </Card>

        <Card className="p-6 border-green-200 hover:border-green-300 hover:shadow-md transition-all">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-green-500 to-green-600 shadow-sm">
              <FileText className="h-5 w-5 text-white" />
            </div>
            <div>
              <h4 className="text-green-900">자동 추출</h4>
              <p className="text-neutral-600 mt-1">
                PDF에서 메타데이터와 텍스트 콘텐츠가 자동으로 추출됩니다
              </p>
            </div>
          </div>
        </Card>

        <Card className="p-6 border-purple-200 hover:border-purple-300 hover:shadow-md transition-all">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-purple-500 to-purple-600 shadow-sm">
              <Database className="h-5 w-5 text-white" />
            </div>
            <div>
              <h4 className="text-purple-900">DB 자동 업로드</h4>
              <p className="text-neutral-600 mt-1">
                처리 완료 후 데이터베이스 연결 시 자동으로 업로드됩니다
              </p>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
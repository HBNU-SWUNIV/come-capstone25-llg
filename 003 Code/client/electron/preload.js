const { contextBridge, ipcRenderer } = require('electron');

/**
 * @description
 * 이 스크립트는 "렌더러(React)"와 "메인(Electron Main)" 간 통신을 연결하는 다리 역할을 합니다.
 * window 객체에 electronAPI를 노출하여 React 코드에서 안전하게 IPC를 사용할 수 있게 합니다.
 */

try { 
  console.log('[Preload] Attempting to expose electronAPI...'); //  실행 시작 로그

  contextBridge.exposeInMainWorld('electronAPI', {
    // -----------------------------
    // 🔹 (React → Main) 요청 함수들
    // -----------------------------

    getInitialData: () => {
      console.log('[Preload] invoking get-initial-data'); 
      return ipcRenderer.invoke('get-initial-data');
    },
    connectDB: (config) => {
      console.log('[Preload] invoking connect-db'); 
      return ipcRenderer.invoke('connect-db', config);
    },
    disconnectDB: () => {
      console.log('[Preload] invoking disconnect-db'); 
      return ipcRenderer.invoke('disconnect-db');
    },
    openPDFFiles: () => {
      console.log('[Preload] invoking open-pdf-files'); 
      return ipcRenderer.invoke('open-pdf-files');
    },

    // files => { name, buffer: ArrayBuffer }[]
    addPDFFiles: (files) => {
      console.log('[Preload] addPDFFiles called in preload.'); 
      try {
        const transportableFiles = files.map(file => {
          return {
            name: file.name,
            buffer: Buffer.from(file.buffer) // ArrayBuffer -> Node.js Buffer
          };
        });
        console.log('[Preload] Files transformed for IPC.'); // 
        console.log('[Preload] invoking add-pdf-files'); 
        return ipcRenderer.invoke('add-pdf-files', transportableFiles);
      } catch (error) {
         console.error('[Preload] Error transforming file buffers:', error); 
         throw error;
      }
    },
    createFolder: (name, color) => {
      console.log('[Preload] invoking create-folder'); 
      return ipcRenderer.invoke('create-folder', name, color);
    },
    
    // 단일 삭제
    deleteDocument: (id, name) => {
      console.log('[Preload] invoking delete-document'); 
      return ipcRenderer.invoke('delete-document', id, name);
    },

    // 다중 삭제 (ID 배열 전달)
    deleteDocuments: (ids) => {
      console.log('[Preload] invoking delete-documents', ids);
      return ipcRenderer.invoke('delete-documents', ids);
    },

    // 단일 이동
    moveToFolder: (documentId, documentName, folderId) => {
      console.log('[Preload] invoking move-to-folder'); 
      return ipcRenderer.invoke('move-to-folder', documentId, documentName, folderId);
    },

    // 다중 이동 (ID 배열 + 폴더명 전달)
    moveDocuments: (ids, folderName) => {
      console.log('[Preload] invoking move-documents', ids, folderName);
      return ipcRenderer.invoke('move-documents', ids, folderName);
    },

    // 문서 상세 내용 조회 (텍스트 청크, 이미지)
    getDocumentContent: (id) => {
      console.log('[Preload] invoking get-document-content', id);
      return ipcRenderer.invoke('get-document-content', id);
    },

    // 문서 다운로드
    downloadDocument: (id, fileName) => {
      console.log('[Preload] invoking download-document', id, fileName);
      return ipcRenderer.invoke('download-document', id, fileName);
    },

    // [추가] 텍스트 청크 수정
    updateTextChunk: (chunkId, newContent) => {
      console.log('[Preload] invoking update-text-chunk', chunkId);
      return ipcRenderer.invoke('update-text-chunk', chunkId, newContent);
    },

    // -----------------------------
    // 🔹 (Main → React) 수신 이벤트
    // -----------------------------
    onDocumentUpdate: (callback) => {
      const listener = (_event, updatedDocument) => {
        console.log('[Preload] Received document-update event.'); // 
        callback(updatedDocument);
      };
      ipcRenderer.on('document-update', listener);
      //  클린업 함수 반환
      return () => ipcRenderer.removeListener('document-update', listener);
    },

    onNewDocument: (callback) => {
      const listener = (_event, newDocument) => {
        console.log('[Preload] Received new-document event.'); // 
        callback(newDocument);
      };
      ipcRenderer.on('new-document', listener);
      // 클린업 함수 반환
      return () => ipcRenderer.removeListener('new-document', listener);
    },


    deleteFolder: (folderId) => ipcRenderer.invoke('delete-folder', folderId),

    deleteTextChunk: (chunkId) => {
      console.log('[Preload] invoking delete-text-chunk', chunkId);
      return ipcRenderer.invoke('delete-text-chunk', chunkId);
    },
    
    deleteImage: (imageId) => {
          console.log('[Preload] invoking delete-image', imageId);
          return ipcRenderer.invoke('delete-image', imageId);
    }

  });
    


  // preload 실행 및 API 노출 성공 로그
  console.log('[Preload] electronAPI exposed successfully.');

} catch (error) {
  //  preload 실행 중 오류 발생 시 로그
  console.error('[Preload] Error exposing electronAPI:', error);
}
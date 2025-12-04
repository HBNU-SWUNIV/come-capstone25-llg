const { app, BrowserWindow, ipcMain, dialog, protocol } = require('electron');
const path = require('path');
const fs = require('fs').promises;
const fsNew = require('fs');
const crypto = require('crypto');
const os = require('os');
const { spawn } = require('child_process');
const { Client } = require('pg');

const isDev = !app.isPackaged;
const devStartUrl = 'http://localhost:3001';

let dbClient = null;
let mainWindow;

protocol.registerSchemesAsPrivileged([
  { 
    scheme: 'app', 
    privileges: { 
      secure: true, 
      standard: true, 
      supportFetchAPI: true, 
      corsEnabled: true 
    } 
  }
]);

function sendToUI(channel, ...args) {
  if (mainWindow) {
    mainWindow.webContents.send(channel, ...args);
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    title: "CustomRAG Database",
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      sandbox: false,
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  if (isDev) {
    mainWindow.loadURL(devStartUrl);
  } else {
    const prodPath = path.join(__dirname, '../out/index.html');
    
    if (fsNew.existsSync(prodPath)) {
      mainWindow.loadURL('app://./index.html');
    } else {
      console.error(`[Main] Error: UI file not found at ${prodPath}`);
    }
  }
}

function initializeIpcHandlers() {
  console.log('[Main] Registering IPC Handlers...');

  const checkDocumentExists = async (pdfName) => {
    if (!dbClient) return false;
    try {
      const query = {
        text: `SELECT 1 FROM Pdf WHERE file_name = $1 LIMIT 1`,
        values: [pdfName],
      };
      const res = await dbClient.query(query);
      return res.rowCount > 0;
    } catch (e) {
      console.error('[Main] Document existence check failed:', e);
      return false;
    }
  };

  const checkFolderExists = async (folderName) => {
    if (!dbClient) return false;
    try {
      const query = {
        text: `SELECT 1 FROM Tag WHERE name = $1 LIMIT 1`,
        values: [folderName],
      };
      const res = await dbClient.query(query);
      return res.rowCount > 0;
    } catch (e) {
      console.error('[Main] Folder existence check failed:', e);
      return false;
    }
  };

  ipcMain.handle('get-initial-data', async () => {
    console.log('[Main] get-initial-data request received');
    
    if (dbClient) {
      try {
        const folderQuery = `
          SELECT id, name, color, created_at as "createdDate" 
          FROM Tag 
          ORDER BY created_at DESC
        `;
        const foldersResult = await dbClient.query(folderQuery);
        const folders = foldersResult.rows;

        const documentQuery = `
          SELECT 
            p.id, 
            p.file_name as name, 
            p.file_size as size, 
            p.upload_date as "uploadDate", 
            p.processed_status as status,
            p.tag_id as "folderId",
            t.name as "folderName"
          FROM Pdf p
          LEFT JOIN Tag t ON p.tag_id = t.id
          ORDER BY p.upload_date DESC
        `;
        const documentsResult = await dbClient.query(documentQuery);

        const documents = documentsResult.rows.map((row) => {
          return {
            id: row.id, 
            name: row.name,
            size: parseInt(row.size, 10) || 0,
            uploadDate: row.uploadDate,
            status: row.status,
            folderId: row.folderId,
            folderName: row.folderName,
            dbUploaded: true,
            pageCount: 0, 
          };
        });
        
        console.log(`[Main] Loaded ${folders.length} folders and ${documents.length} documents.`);
        return { folders: folders, documents: documents };

      } catch (error) {
        console.error('[Main] Failed to load initial data:', error.message);
        return { folders: [], documents: [] };
      }
    } else {
      return { folders: [], documents: [] };
    }
  });

  ipcMain.handle('connect-db', async (event, config) => {
    console.log('[Main] connect-db request received');
    console.log("config:", config);
    console.log("password type:", typeof config.password);
    
    if (dbClient) {
      try {
        await dbClient.end();
      } catch (e) {
        console.error(e.message);
      }
      dbClient = null;
    }

    dbClient = new Client(config);

    try {
      await dbClient.connect();
      await dbClient.query('SELECT NOW()');
      return true;
    } catch (error) {
      console.error('[Main] DB connection failed:', error.message);
      dbClient = null;
      return false;
    }
  });

  ipcMain.handle('disconnect-db', async () => {
    if (!dbClient) return true;
    try {
      await dbClient.end();
      dbClient = null;
      return true;
    } catch (error) {
      dbClient = null;
      return false;
    }
  });

  ipcMain.handle('open-pdf-files', async () => {
    const { filePaths } = await dialog.showOpenDialog({
      title: 'Select PDF Files',
      filters: [{ name: 'PDFs', extensions: ['pdf'] }],
      properties: ['openFile', 'multiSelections'],
    });

    if (!filePaths || filePaths.length === 0) return;

    const newDocuments = [];
    const validFilePaths = [];

    for (const filePath of filePaths) {
      const baseName = path.basename(filePath);

      const exists = await checkDocumentExists(baseName);
      if (exists) {
        sendToUI('toast', { type: 'warning', message: `이미 존재하는 문서입니다: ${baseName}` });
        continue; 
      }

      if (newDocuments.some(doc => doc.name === baseName)) {
        continue;
      }

      const stats = fsNew.statSync(filePath);
      const newDocId = crypto.randomUUID();

      validFilePaths.push(filePath);
      newDocuments.push({
        id: newDocId,
        name: baseName,
        _tempBaseName: baseName,
        size: stats.size,
        uploadDate: new Date(),
        status: 'processing',
        dbUploaded: false,
      });
    }
    
    if (newDocuments.length === 0) return;

    newDocuments.forEach(doc => sendToUI('new-document', doc));
    await processAndUploadPdfs(newDocuments, validFilePaths);
  });

  ipcMain.handle('add-pdf-files', async (event, files) => {
    if (!files || files.length === 0) return;

    const tempDir = os.tmpdir();
    const tempFilePaths = [];
    const newDocuments = [];
    
    try {
      for (const fileObj of files) {
        const exists = await checkDocumentExists(fileObj.name);
        if (exists) {
          sendToUI('toast', { type: 'warning', message: `이미 존재하는 문서입니다: ${fileObj.name}` });
          continue;
        }

        try {
          const uniqueSuffix = crypto.randomUUID();
          const tempBaseName = `${uniqueSuffix}-${fileObj.name}`;
          const tempFilePath = path.join(tempDir, tempBaseName);
          
          await fs.writeFile(tempFilePath, fileObj.buffer);
          tempFilePaths.push(tempFilePath);

          const stats = await fs.stat(tempFilePath);
          const newDocId = crypto.randomUUID();
          newDocuments.push({
            id: newDocId,
            name: fileObj.name,
            _tempBaseName: tempBaseName,
            size: stats.size,
            uploadDate: new Date(),
            status: 'processing',
            dbUploaded: false,
          });

        } catch (error) {
          console.error(`[Main] Error saving temp file ${fileObj.name}:`, error);
        }
      }

      if (newDocuments.length === 0) return;

      newDocuments.forEach(doc => sendToUI('new-document', doc));
      await processAndUploadPdfs(newDocuments, tempFilePaths);

    } finally {
      for (const tempPath of tempFilePaths) {
        try {
          await fs.unlink(tempPath);
        } catch (delError) {
          console.error(delError);
        }
      }
    }
  });
  
  ipcMain.handle('create-folder', async (event, name, color) => {
    if (!dbClient) throw new Error('DB not connected');

    const exists = await checkFolderExists(name);
    if (exists) {
      return null;
    }

    try {
      const res = await dbClient.query(
        `INSERT INTO Tag (id, name, color) VALUES ($1, $2, $3) RETURNING *`,
        [crypto.randomUUID(), name, color]
      );
      return {
        id: res.rows[0].id,
        name: res.rows[0].name,
        color: res.rows[0].color,
        createdDate: res.rows[0].created_at
      };
    } catch (e) {
      console.error('[Main] Create folder failed:', e.message);
      throw e;
    }
  });

  // 단일 문서 삭제
  ipcMain.handle('delete-document', async (event, documentId, documentName) => {
    if (!dbClient) throw new Error('DB not connected');

    try {
      await dbClient.query(`DELETE FROM Pdf WHERE id = $1`, [documentId]);
      console.log(`[Main] Deleted document ${documentId}`);
      return true; 
    } catch (error) {
      console.error('[Main] Delete document failed:', error.message);
      throw error;
    }
  });

  // 다중 문서 삭제 핸들러
  ipcMain.handle('delete-documents', async (event, documentIds) => {
    if (!dbClient) throw new Error('DB not connected');

    if (!Array.isArray(documentIds) || documentIds.length === 0) {
      return { success: false, deletedCount: 0 };
    }

    try {
      // Postgres ANY 문법을 사용하여 배열 내 ID 일괄 삭제
      const query = `DELETE FROM Pdf WHERE id = ANY($1)`;
      const res = await dbClient.query(query, [documentIds]);
      
      console.log(`[Main] Batch deleted ${res.rowCount} documents.`);
      return { success: true, deletedCount: res.rowCount }; 
    } catch (error) {
      console.error('[Main] Batch delete documents failed:', error.message);
      throw error;
    }
  });

  // 단일 문서 이동
  ipcMain.handle('move-to-folder', async (event, documentId, documentName, folderName) => {
    if (!dbClient) throw new Error('DB not connected');

    try {
      let tagId = null;

      if (folderName) {
        const tagRes = await dbClient.query(`SELECT id FROM Tag WHERE name = $1`, [folderName]);
        if (tagRes.rowCount > 0) {
          tagId = tagRes.rows[0].id;
        } else {
          throw new Error(`Folder not found: ${folderName}`);
        }
      }

      await dbClient.query(`UPDATE Pdf SET tag_id = $1 WHERE id = $2`, [tagId, documentId]);
      return true;
    } catch (error) {
      console.error('[Main] Move folder failed:', error.message);
      throw error;
    }
  });

  // 다중 문서 이동 핸들러
  ipcMain.handle('move-documents', async (event, documentIds, folderName) => {
    if (!dbClient) throw new Error('DB not connected');

    if (!Array.isArray(documentIds) || documentIds.length === 0) {
      return { success: false, movedCount: 0 };
    }

    try {
      let tagId = null;

      if (folderName) {
        const tagRes = await dbClient.query(`SELECT id FROM Tag WHERE name = $1`, [folderName]);
        if (tagRes.rowCount > 0) {
          tagId = tagRes.rows[0].id;
        } else {
          // 폴더 이름이 있지만 DB에 없는 경우 (에러 처리 또는 루트로 간주)
          throw new Error(`Folder not found: ${folderName}`);
        }
      }

      // Postgres ANY 문법을 사용하여 배열 내 ID 일괄 업데이트
      const query = `UPDATE Pdf SET tag_id = $1 WHERE id = ANY($2)`;
      const res = await dbClient.query(query, [tagId, documentIds]);
      
      console.log(`[Main] Batch moved ${res.rowCount} documents to ${folderName || 'root'}.`);
      return { success: true, movedCount: res.rowCount };
    } catch (error) {
      console.error('[Main] Batch move documents failed:', error.message);
      throw error;
    }
  });

  // -------------------------------------------------------
  // [추가] 보기(View), 다운로드(Download), 수정(Edit) 핸들러
  // -------------------------------------------------------

  // 1. 문서 상세 콘텐츠 조회 (텍스트 청크, 이미지)
  ipcMain.handle('get-document-content', async (event, documentId) => {
    if (!dbClient) throw new Error('DB not connected');

    try {
      // 1) PDF 정보 조회
      const pdfRes = await dbClient.query(`SELECT file_name FROM Pdf WHERE id = $1`, [documentId]);
      if (pdfRes.rowCount === 0) throw new Error('Document not found');
      const fileName = pdfRes.rows[0].file_name;

      // 2) 텍스트 청크 조회
      const textRes = await dbClient.query(
        `SELECT id, content, chunk_index, metadata FROM Text WHERE pdf_id = $1 ORDER BY chunk_index ASC`,
        [documentId]
      );

      // 3) 이미지 조회
      const imageRes = await dbClient.query(
        `SELECT id, image_data, image_index FROM Image WHERE pdf_id = $1 ORDER BY image_index ASC`,
        [documentId]
      );

      // 이미지 Buffer -> Base64 변환
      const images = imageRes.rows.map(row => ({
        id: row.id,
        index: row.image_index,
        src: `data:image/png;base64,${row.image_data.toString('base64')}`
      }));

      return {
        success: true,
        fileName: fileName,
        textChunks: textRes.rows,
        images: images
      };

    } catch (error) {
      console.error('[Main] Get document content failed:', error.message);
      return { success: false, error: error.message };
    }
  });

  // 2. 문서(PDF) 다운로드
  ipcMain.handle('download-document', async (event, documentId, defaultName) => {
    if (!dbClient) throw new Error('DB not connected');

    try {
      // Raw ID 찾기
      const pdfRes = await dbClient.query(`SELECT raw_id FROM Pdf WHERE id = $1`, [documentId]);
      if (pdfRes.rowCount === 0) throw new Error('Document not found');
      const rawId = pdfRes.rows[0].raw_id;

      // Raw Data(Binary) 가져오기
      const rawRes = await dbClient.query(`SELECT file_data FROM Raw WHERE id = $1`, [rawId]);
      if (rawRes.rowCount === 0) throw new Error('Raw data not found');
      
      const fileBuffer = rawRes.rows[0].file_data;

      // 저장 다이얼로그 표시
      const { canceled, filePath } = await dialog.showSaveDialog({
        title: 'Save PDF',
        defaultPath: defaultName || 'document.pdf',
        filters: [{ name: 'PDF Files', extensions: ['pdf'] }]
      });

      if (canceled || !filePath) return { success: false, message: 'Canceled' };

      // 파일 쓰기
      await fs.writeFile(filePath, fileBuffer);
      return { success: true, filePath };

    } catch (error) {
      console.error('[Main] Download failed:', error.message);
      return { success: false, message: error.message };
    }
  });

  // 3. 텍스트 청크 수정
  ipcMain.handle('update-text-chunk', async (event, chunkId, newContent) => {
    if (!dbClient) throw new Error('DB not connected');
    
    try {
      await dbClient.query(
        `UPDATE Text SET content = $1 WHERE id = $2`,
        [newContent, chunkId]
      );
      return { success: true };
    } catch (error) {
      console.error('[Main] Update text chunk failed:', error.message);
      return { success: false, error: error.message };
    }
  });

  ipcMain.handle('delete-folder', async (event, folderId) => {
    if (!dbClient) throw new Error('DB not connected');

    try {
      // 해당 폴더에 속한 문서들을 루트로 이동 
      await dbClient.query(`UPDATE Pdf SET tag_id = NULL WHERE tag_id = $1`, [folderId]);
      
      // 폴더 삭제
      await dbClient.query(`DELETE FROM Tag WHERE id = $1`, [folderId]);
      
      console.log(`[Main] Deleted folder ${folderId}`);
      return { success: true };
    } catch (error) {
      console.error('[Main] Delete folder failed:', error.message);
      throw error;
    }
  });
 ipcMain.handle('delete-text-chunk', async (event, chunkId) => {
    if (!dbClient) throw new Error('DB not connected');
    
    try {
      await dbClient.query(`DELETE FROM Text WHERE id = $1`, [chunkId]);
      console.log(`[Main] Deleted text chunk ${chunkId}`);
      return { success: true };
    } catch (error) {
      console.error('[Main] Delete text chunk failed:', error.message);
      return { success: false, error: error.message };
    }
  });

  ipcMain.handle('delete-image', async (event, imageId) => {
    if (!dbClient) throw new Error('DB not connected');
    
    try {
      await dbClient.query(`DELETE FROM Image WHERE id = $1`, [imageId]);
      console.log(`[Main] Deleted image ${imageId}`);
      return { success: true };
    } catch (error) {
      console.error('[Main] Delete image failed:', error.message);
      return { success: false, error: error.message };
    }
  });

}

async function processAndUploadPdfs(newDocuments, filePaths) {
  const pythonScriptFilename = 'uni_processor.py';
  const scriptPath = isDev
    ? path.join(__dirname, '../parser/scripts/', pythonScriptFilename)
    : path.join(process.resourcesPath, 'python/scripts/', pythonScriptFilename);
  
  if (!isDev && !fsNew.existsSync(scriptPath)) {
    throw new Error('Python script not found.');
  }

  const outputDir = path.join(app.getPath('userData'), 'rag_output_temp');
  
  if (!fsNew.existsSync(outputDir)) {
    fsNew.mkdirSync(outputDir, { recursive: true });
  }
  
  const originalStems = newDocuments.map(doc => path.parse(doc.name).name);

  const args = [
    '--input-files', ...filePaths,
    '--original-stems', ...originalStems,
    '--output-dir', outputDir, 
  ];
  
  try {
    const result = await runPythonScript(scriptPath, args);
    const allData = JSON.parse(result.jsonOutput);
    
    const processedResults = allData.summary || [];
    const textChunks = allData.text_chunks || [];
    const imageChunks = allData.image_chunks || [];
    
    const resultMap = new Map(
      processedResults.map(r => [r.baseName, r])
    );

    for (const doc of newDocuments) {
      const processedFile = resultMap.get(doc._tempBaseName);
      
      if (processedFile && processedFile.status === 'success') {
        const updatedDocument = {
          ...doc,
          status: 'ready',
        };
        sendToUI('document-update', updatedDocument);
      } else {
        console.error(`[Main] Processing failed for ${doc.name}`);
        sendToUI('document-update', { ...doc, status: 'error' });
      }
    }

    if (dbClient) {
      console.log(`[Main] Starting DB Upload...`);

      for (let i = 0; i < filePaths.length; i++) {
        const filePath = filePaths[i];
        const docInfo = newDocuments[i];
        const pdfNameStem = path.parse(docInfo.name).name;
        
        const processedStatus = resultMap.get(docInfo._tempBaseName);
        if (!processedStatus || processedStatus.status !== 'success') {
          continue;
        }

        try {
          await dbClient.query('BEGIN');

          const fileBuffer = await fs.readFile(filePath);
          const rawQuery = `INSERT INTO Raw (file_data) VALUES ($1) RETURNING id`;
          const rawRes = await dbClient.query(rawQuery, [fileBuffer]);
          const rawId = rawRes.rows[0].id;

          const pdfQuery = `
            INSERT INTO Pdf (id, raw_id, file_name, file_size, processed_status)
            VALUES ($1, $2, $3, $4, 'ready') RETURNING id
          `;
          const pdfRes = await dbClient.query(pdfQuery, [docInfo.id, rawId, docInfo.name, docInfo.size]);
          const pdfId = pdfRes.rows[0].id; 

          const docTextChunks = textChunks.filter(c => c.source === pdfNameStem);
          for (let idx = 0; idx < docTextChunks.length; idx++) {
            const chunk = docTextChunks[idx];
            await dbClient.query(
              `INSERT INTO Text (pdf_id, content, chunk_index, metadata) VALUES ($1, $2, $3, $4)`,
              [pdfId, chunk.text, idx, chunk.metadata || {}]
            );
          }

          const docImageChunks = imageChunks.filter(c => c.source === pdfNameStem);
          for (let idx = 0; idx < docImageChunks.length; idx++) {
            const img = docImageChunks[idx];
            if (!img.data_base64) continue;

            const imageId = img.image_id || img.filename || `${pdfNameStem}_img_${idx}.png`;
            const imgBuffer = Buffer.from(img.data_base64, 'base64');
            
            await dbClient.query(
              `INSERT INTO Image (id, pdf_id, image_data, image_index) VALUES ($1, $2, $3, $4)`,
              [imageId, pdfId, imgBuffer, idx]
            );
          }

          await dbClient.query('COMMIT');
          console.log(`[Main] DB Upload success: ${docInfo.name}`);

          sendToUI('document-update', { ...docInfo, id: pdfId, dbUploaded: true, status: 'ready' });

        } catch (dbErr) {
          await dbClient.query('ROLLBACK');
          console.error(`[Main] DB Upload error for ${docInfo.name}:`, dbErr);
          sendToUI('document-update', { ...docInfo, status: 'error' });
        }
      }
    } else {
        throw new Error('DB not connected, skipping upload.');
    }

  } catch (error) {
    console.error('[Main] Critical error in processing:', error.message);
    if (dbClient) {
      try { await dbClient.query('ROLLBACK'); } catch (rbError) { }
    }
    for (const doc of newDocuments) {
      sendToUI('document-update', { ...doc, status: 'error' });
    }
  } finally {
    try {
      if (fsNew.existsSync(outputDir)) {
        fsNew.rmSync(outputDir, { recursive: true, force: true });
      }
    } catch (delError) {
      console.error(delError);
    }
  }
}

function runPythonScript(scriptPath, args) {
  return new Promise((resolve, reject) => {
    const platform = os.platform();
    let basePythonCommand;
    if (platform === 'win32') {
        basePythonCommand = 'python';
    } else {
        basePythonCommand = 'python3';
    }

    const pythonExecutable = basePythonCommand;
    console.log(`[Main] Executing Python: ${pythonExecutable} ${scriptPath} ${args.join(' ')}`);

    const pyProcess = spawn(pythonExecutable, [scriptPath, ...args]);

    pyProcess.on('error', (err) => {
        console.error(`[Main] Failed to spawn python process: ${err.message}`);
        reject(new Error(`Python process failed to start: ${err.message}`));
    });

    let jsonOutput = ''; 
    let stderr = '';     

    pyProcess.stdout.on('data', (data) => {
      jsonOutput += data.toString();
    }); 

    pyProcess.stderr.on('data', (data) => {
      stderr += data.toString();
      console.log(`[Python Log]: ${data.toString().trim()}`);
    });

    pyProcess.on('close', (code) => {
      if (code === 0) {
        if (jsonOutput.trim() === '') {
            reject(new Error(stderr || `Python script finished with code 0 but no output.`));
        } else {
            resolve({ success: true, jsonOutput: jsonOutput });
        }
      } else {
        reject(new Error(stderr || `Python script failed with code ${code}`));
      }
    });
  });
}

app.on('ready', () => {
  initializeIpcHandlers();

  if (!isDev) {
    protocol.registerFileProtocol('app', (request, callback) => {
      let urlPath = request.url.substr(6); 
      if (urlPath.startsWith('./')) {
        urlPath = urlPath.substr(2);
      }
      const decodedPath = decodeURI(urlPath);
      const filePath = path.join(__dirname, '../out', decodedPath);

      if (fsNew.existsSync(filePath)) {
        callback({ path: filePath });
      } else {
        callback({ error: -6 });
      }
    });
  }
  
  createWindow();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
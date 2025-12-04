import os
import sys
import json
import fitz
import argparse
import base64 # 👈 [추가] Base64 인코딩을 위해 추가
from pathlib import Path

# 프로젝트 root path 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pdf_processor.core.extractor import PDFExtractor
from pdf_processor.utils.file_utils import FileUtils

def log_to_stderr(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

# 🔽 [추가] 이미지 파일을 읽어 Base64로 인코딩하는 헬퍼 함수
def encode_image_to_base64(image_path):
    """
    이미지 파일 경로를 받아 Base64 문자열로 반환합니다.
    """
    if not os.path.exists(image_path):
        log_to_stderr(f"Warning: Image file not found at {image_path}")
        return None
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        log_to_stderr(f"Error encoding image {image_path}: {e}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process PDF files and extract content")
    
    parser.add_argument("--input-files", required=True, nargs='+', help="List of input PDF files")
    parser.add_argument("--original-stems", required=True, nargs='+', help="List of original PDF file stems")
    
    parser.add_argument("--output-dir", required=True, help="Temporary output directory")
    
    parser.add_argument("--chunk-size", type=int, default=1024)
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--overlap-threshold", type=float, default=0.7)
    args = parser.parse_args()

    if len(args.input_files) != len(args.original_stems):
        log_to_stderr(f"Error: Mismatch count --input-files ({len(args.input_files)}) vs --original-stems ({len(args.original_stems)})")
        sys.exit(1)

    FileUtils.ensure_directory(args.output_dir)

    processor = PDFExtractor(
        chunk_size=args.chunk_size,
        dpi=args.dpi,
        overlap_threshold=args.overlap_threshold
    )

    all_text_chunks = []
    all_image_chunks = []
    results_list = []
    
    all_successful = True 

    for pdf_file, original_stem in zip(args.input_files, args.original_stems):
        base_pdf_name = os.path.basename(pdf_file)

        if not os.path.exists(pdf_file):
            log_to_stderr(f"File not found, skipping: {pdf_file}")
            results_list.append({"baseName": base_pdf_name, "status": "error", "message": "File not found"})
            all_successful = False
            continue

        log_to_stderr(f"Processing: {pdf_file} (as {original_stem})")
        
        page_count = 0
        try:
            with fitz.open(pdf_file) as doc:
                page_count = doc.page_count

            pdf_output_dir = os.path.join(args.output_dir, original_stem)
            FileUtils.ensure_directory(pdf_output_dir)

            all_chunks_list_raw = processor.extract_content(
                pdf_path=pdf_file,
                output_dir=pdf_output_dir
            )

            # 🔽 [수정] Extractor의 반환값을 단일 리스트로 정규화
            content_list_raw = []
            if isinstance(all_chunks_list_raw, tuple) and len(all_chunks_list_raw) == 2:
                content_list_raw.extend(all_chunks_list_raw[0])
                content_list_raw.extend(all_chunks_list_raw[1])
            elif isinstance(all_chunks_list_raw, list):
                content_list_raw = all_chunks_list_raw
            else:
                raise ValueError(f"Extractor returned unexpected type: {type(all_chunks_list_raw)}. Expected tuple or list.")

            # 1. [수정] "현재 기능" 유지: *포맷팅 전*에 텍스트와 이미지로 분리
            text_content_list = []
            image_content_list = []
            
            # 🔽 [제거] 디버깅 로그 제거
            # log_to_stderr(f"--- Debugging chunks for {original_stem} (Total: {len(content_list_raw)}) ---")
            
            for i, chunk in enumerate(content_list_raw):
                # 🔽 [제거] 디버깅 로그 제거
                # chunk_keys = list(chunk.keys()) if isinstance(chunk, dict) else f"Not a dict: {type(chunk)}"
                # log_to_stderr(f"Chunk {i} Keys: {chunk_keys}")

                # 🔽 [수정] 이미지 식별 로직을 "image_path" 키 존재 여부로 변경
                is_image = "image_path" in chunk
                
                if is_image:
                    image_content_list.append(chunk)
                else:
                    text_content_list.append(chunk)
            
            # 🔽 [제거] 디버깅 로그 제거
            # log_to_stderr(f"--- Debugging finished (Found {len(image_content_list)} images) ---")

            # 2. [수정] "기존 코드" 로직: *텍스트 리스트*만 포맷터에 전달
            formatted_text = processor.formatter.format_for_jsonl(text_content_list, original_stem)
            
            # (변경 없음) "pdfName" (source) NULL 오류 방어 코드
            for chunk in formatted_text:
                if not chunk.get("source"): 
                    log_to_stderr(f"Warning: Chunk found with missing 'source'. Manually setting to '{original_stem}'.")
                    chunk["source"] = original_stem

            all_text_chunks.extend(formatted_text)

            # 3. [수정] "현재 기능" 유지: *이미지 리스트*는 수동으로 포맷팅
            formatted_images = []
            for img_chunk in image_content_list:
                # 🔽 [수정] 이미지 청크에서 'path' (또는 'src', 'image_path') 키를 찾아 Base64로 인코딩
                image_path = img_chunk.get("image_path", img_chunk.get("path", img_chunk.get("src")))
                base64_data = None

                if image_path:
                    # 'path'가 output_dir을 기준으로 하는지, 절대 경로인지 확인
                    if not os.path.isabs(image_path):
                        # 🔽 [수정] 중복 경로(stem/stem) 버그 수정
                        # Extractor가 반환한 경로는 'output_dir' 기준 (예: 'stem/image.png')
                        image_path = os.path.join(args.output_dir, image_path)
                    base64_data = encode_image_to_base64(image_path)
                else:
                    log_to_stderr(f"Warning: Image chunk found without 'image_path' key for {original_stem}.")
                
                formatted_images.append({
                    "source": original_stem, # 이미지에도 'source' 설정
                    "data_base64": base64_data, # 👈 Base64 데이터
                    "metadata": img_chunk.get("metadata", {})
                })
            all_image_chunks.extend(formatted_images)

            log_to_stderr(f"Successfully processed: {pdf_file} (Text: {len(formatted_text)}, Images: {len(formatted_images)})")
            
            results_list.append({
                "baseName": base_pdf_name,
                "originalStem": original_stem,
                "status": "success",
                "pageCount": page_count,
                "textChunkCount": len(formatted_text),
                "imageChunkCount": len(formatted_images)
            })

        except Exception as e:
            log_to_stderr(f"Error processing {pdf_file}: {e}")
            results_list.append({"baseName": base_pdf_name, "status": "error", "message": str(e), "pageCount": page_count})
            all_successful = False
            continue
    
    final_output = {
        "summary": results_list,
        "text_chunks": all_text_chunks,
        "image_chunks": all_image_chunks
    }
    
    print(json.dumps(final_output))

    if not all_successful:
        log_to_stderr("One or more files failed to process.")
        sys.exit(1)

    # try:
    #     output_json_path = Path(args.output_dir) / "uni_processor_output.json"
    #     with open(output_json_path, "w", encoding="utf-8") as f:
    #         json.dump(final_output, f, ensure_ascii=False, indent=2)
    #     log_to_stderr(f"Saved final_output JSON to: {output_json_path}")
    # except Exception as e:
    #     log_to_stderr(f"Error saving final_output JSON: {e}")


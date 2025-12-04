import os
import sys
import glob
import json
from pathlib import Path

# 프로젝트 root path 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pdf_processor.core.extractor import PDFExtractor
from pdf_processor.utils.file_utils import FileUtils


def process_pdfs(
    input_dir: str,
    output_dir: str,
    jsonl_output: str = None,
    chunk_size: int = 1024,
    dpi: int = 300,
    overlap_threshold: float = 0.7
):
    """
    PDF 폴더를 처리하고 JSONL로 저장하는 함수
    """
    FileUtils.ensure_directory(output_dir)
    log_file_path = os.path.join(output_dir, "processed_pdfs.log")
    processed_files = FileUtils.get_processed_pdfs(log_file_path)

    pdf_files = glob.glob(os.path.join(input_dir, "*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in '{input_dir}'.")

    processor = PDFExtractor(
        chunk_size=chunk_size,
        dpi=dpi,
        overlap_threshold=overlap_threshold
    )

    if jsonl_output:
        jsonl_output_path = jsonl_output
    else:
        jsonl_output_path = os.path.join(output_dir, "corpus.jsonl")

    all_formatted_content = []

    for pdf_file in pdf_files:
        base_pdf_name = os.path.basename(pdf_file)
        if base_pdf_name in processed_files:
            print(f"Skipping already processed: {pdf_file}")
            continue

        print(f"Processing: {pdf_file}")
        try:
            content_list = processor.extract_content(pdf_path=pdf_file, output_dir=output_dir)
            FileUtils.log_processed_pdf(log_file_path, base_pdf_name)

            pdf_name = os.path.splitext(base_pdf_name)[0]
            formatted_content = processor.formatter.format_for_jsonl(content_list, pdf_name)
            all_formatted_content.extend(formatted_content)

            print(f"Successfully processed: {pdf_file} ({len(formatted_content)} chunks)")

        except Exception as e:
            print(f"Error processing {pdf_file}: {e}")
            continue

    if all_formatted_content:
        with open(jsonl_output_path, 'w', encoding='utf-8') as f:
            for item in all_formatted_content:
                json.dump(item, f, ensure_ascii=False)
                f.write('\n')
        print(f"JSONL output saved to: {jsonl_output_path}")
        print(f"Total processed chunks: {len(all_formatted_content)}")
    else:
        print("No content was processed successfully.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Process PDF files and extract content")
    parser.add_argument("--input-dir", required=True, help="Input PDF directory")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--jsonl-output", help="JSONL output file path")
    parser.add_argument("--chunk-size", type=int, default=1024)
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--overlap-threshold", type=float, default=0.7)
    args = parser.parse_args()

    process_pdfs(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        jsonl_output=args.jsonl_output,
        chunk_size=args.chunk_size,
        dpi=args.dpi,
        overlap_threshold=args.overlap_threshold
    )
import os
import argparse
import sys
import glob
import json

from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from pdf_processor.core.extractor import PDFExtractor
from pdf_processor.utils.file_utils import FileUtils

def main():
    parser = argparse.ArgumentParser(description='Process PDF files and extract content')
    parser.add_argument('--input-dir', required=True, help='Input PDF directory')
    parser.add_argument('--output-dir', required=True, help='Output directory')
    parser.add_argument('--jsonl-output', help='JSONL output file path')
    parser.add_argument('--chunk-size', type=int, default=1024, help='Text chunk size')
    parser.add_argument('--dpi', type=int, default=300, help='DPI for image extraction')
    parser.add_argument('--overlap-threshold', type=float, default=0.7, help='Overlap threshold for text-table detection')
    
    args = parser.parse_args()

    FileUtils.ensure_directory(args.output_dir)

    log_file_path = os.path.join(args.output_dir, "processed_pdfs.log")

    processed_files = FileUtils.get_processed_pdfs(log_file_path)

    pdf_files = glob.glob(os.path.join(args.input_dir, "*.pdf"))
    if not pdf_files:
        print(f"Error: No PDF files found in '{args.input_dir}'.")
        sys.exit(1)

    print(f"Found {len(pdf_files)} PDF files to process.")

    processor = PDFExtractor(
        chunk_size=args.chunk_size,
        dpi=args.dpi,
        overlap_threshold=args.overlap_threshold
    )

    if args.jsonl_output:
        jsonl_output_path = args.jsonl_output
    else:
        jsonl_output_path = os.path.join(args.output_dir, "processed_pdfs.jsonl")

    all_formatted_content = []

    for pdf_file in pdf_files:
        base_pdf_name = os.path.basename(pdf_file)
        if base_pdf_name in processed_files:
            print(f"Skipping already processed: {pdf_file}")
            continue

        print(f"Processing: {pdf_file}")
        try:
            content_list = processor.extract_content(pdf_path=pdf_file, output_dir=args.output_dir)
            
            FileUtils.log_processed_pdf(log_file_path, base_pdf_name)
            
            pdf_name = os.path.splitext(base_pdf_name)[0]
            
            formatted_content = processor.formatter.format_for_jsonl(content_list, pdf_name)
            all_formatted_content.extend(formatted_content)
            
            print(f"Successfully processed: {pdf_file} ({len(formatted_content)} chunks)")
            
        except Exception as e:
            print(f"Error processing {pdf_file}: {e}")
            continue

    if all_formatted_content:
        try:
            with open(jsonl_output_path, 'w', encoding='utf-8') as f:
                for item in all_formatted_content:
                    json.dump(item, f, ensure_ascii=False)
                    f.write('\n')
            print(f"JSONL output saved to: {jsonl_output_path}")
            print(f"Total processed chunks: {len(all_formatted_content)}")
        except Exception as e:
            print(f"Error saving JSONL file: {e}")
    else:
        print("No content was processed successfully.")

if __name__ == "__main__":
    main()
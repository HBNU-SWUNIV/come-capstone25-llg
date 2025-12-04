
import os
from pathlib import Path

DEFAULT_CHUNK_SIZE = 1024
DEFAULT_DPI = 300
DEFAULT_OVERLAP_THRESHOLD = 0.7

SUPPORTED_IMAGE_FORMATS = ['png', 'jpg', 'jpeg', 'bmp', 'tiff']
PDF_EXTENSION = '.pdf'

TABLE_TOKEN_FORMAT = "[TABLE_{pdf_name}_{counter:04d}]"
IMAGE_TOKEN_FORMAT = "[IMAGE_{pdf_name}_{counter:04d}]"

TABLE_FILENAME_PATTERN = "{pdf_name}_{counter:04d}_table.png"
IMAGE_FILENAME_PATTERN = "{pdf_name}_{counter:04d}_image.{ext}"
IMAGE_AREA_FILENAME_PATTERN = "{pdf_name}_{counter:04d}_image_area.png"

SOT_TAG = "[SOT]"
EOT_TAG = "[EOT]"

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO'
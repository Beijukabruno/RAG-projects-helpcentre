#!/bin/bash

PDF_DIR="./cacx_pdfs"
MD_DIR="./cacx_markdown"

mkdir -p "$MD_DIR"

echo "Converting PDFs from: $PDF_DIR"
echo "Writing Markdown to: $MD_DIR"

npx @opendocsg/pdf2md \
    --inputFolderPath="$PDF_DIR" \
    --outputFolderPath="$MD_DIR"

import gc
from pathlib import Path
from typing import List, Tuple

from docling_core.types.doc import PictureItem, TableItem
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from core.config import settings
from core.logging import get_logger

logger = get_logger()


class DoclingProcessing:
    def __init__(self):
        self.DATA_DIR = settings.DATA_DIR
        self.OUTPUT_MD_DIR = settings.OUTPUT_MD_DIR
        self.OUTPUT_IMAGES_DIR = settings.OUTPUT_IMAGES_DIR
        self.OUTPUT_TABLES_DIR = settings.OUTPUT_TABLES_DIR

    def extract_metadata_from_filename(self, filename: str):
        """
        Extract metadata from filename.
        
        Expected format: CompanyName DocType [Quarter] Year.pdf
        Examples:
            - Amazon 10-Q Q1 2024.pdf
            - Microsoft 10-K 2023.pdf
        """
        filename = filename.replace('.pdf', '').replace('.md', '')
        parts = filename.split()

        return {
            'company_name': parts[0],
            'doc_type': parts[1],
            'fiscal_quarter': parts[2] if len(parts)==4 else None,
            'fiscal_year': parts[-1]
        }


    def convert_pdf_to_docling(self, pdf_file: Path):

        pipeline_options = PdfPipelineOptions()
        pipeline_options.images_scale = 2
        pipeline_options.generate_picture_images = True
        pipeline_options.generate_page_images = True

        logger.info("Pipeline options set")

        doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        logger.info("Document converter created")
        return doc_converter.convert(pdf_file)


    def save_page_images(self, doc_converter, images_dir: Path):
        """
        Find and save pages with large images (>500x500 pixels).
        """
        pages_to_save = set()

        for item in doc_converter.document.iterate_items():
            element = item[0]

            if isinstance(element, PictureItem):
                image = element.get_image(doc_converter.document)

                if image.size[0]>500 and image.size[1]>500:
                    # prov tells from which source bounding box the page no is coming
                    page_no = element.prov[0].page_no if element.prov else None

                    if page_no:
                        logger.info(f"Found large image on page {page_no}")
                        pages_to_save.add(page_no)


            # save images
            for page_no in pages_to_save:
                page = doc_converter.document.pages[page_no]
                logger.info(f"Saving page {page_no}")
                page.image.pil_image.save(images_dir/ f"page_{page_no}.png", "PNG")


    def extract_context_and_table(self, lines: List[str], table_index: int):
        """
        Extract context and table content at a specific position.
        
        Args:
            lines: All markdown lines
            table_index: Where the table starts
        
        Returns:
            (combined_content, next_line_index)
        """
        table_lines = []
        i = table_index

        while (i < len(lines)) and (lines[i].startswith('|')):
            table_lines.append(lines[i])
            i = i + 1

        start = max(0, table_index-2)
        context_lines = lines[start: table_index]

        logger.info(f"Extracting table {table_index}")
        content = '\n'.join(context_lines) + '\n\n' + '\n'.join(table_lines)
        return content, i


    def extract_tables_with_context(self, markdown_text: str):
        """
        Find all tables and extract them with context and page numbers.
        
        Returns:
            List of (content, table_name, page_number)
        """
        logger.info("Extracting tables with context")
        lines = markdown_text.split('\n')
        lines = [line for line in lines if line.strip()]
        tables = []
        current_page = 1
        table_num = 1
        i = 0

        while(i< len(lines)):
            if '<!-- page break -->' in lines[i]:
                current_page = current_page + 1
                i = i + 1
                continue

            if lines[i].startswith('|') and lines[i].count('|') > 1:
                content, next_i = self.extract_context_and_table(lines, i)

                tables.append((content, f"table_{table_num}", current_page))
                table_num = table_num + 1
                i = next_i

            else:
                i = i + 1

        return tables


    def save_tables(self, markdown_text, tables_dir):

        tables = self.extract_tables_with_context(markdown_text)

        for table_content, table_name, page_num in tables:
            logger.info(f"Saving table {table_name} on page {page_num}")
            content_with_page = f"**Page:** {page_num}\n\n{table_content}"

            (tables_dir/f"{table_name}_page_{page_num}.md").write_text(content_with_page, encoding='utf-8')


    def extract_pdf_content(self, pdf_file: Path, converter: DocumentConverter):
        """
        Processes a single PDF and ensures memory is released afterward.
        """
        try:
            metadata = self.extract_metadata_from_filename(pdf_file.name)
            company_name = metadata['company_name']

            # Setup paths
            md_dir = Path(self.OUTPUT_MD_DIR) / company_name
            images_dir = Path(self.OUTPUT_IMAGES_DIR) / company_name / pdf_file.stem
            tables_dir = Path(self.OUTPUT_TABLES_DIR) / company_name / pdf_file.stem
            
            for dir_path in [md_dir, images_dir, tables_dir]:
                dir_path.mkdir(parents=True, exist_ok=True)

            logger.info("Converting PDF to Docling")
            result = converter.convert(pdf_file)

            logger.info("Exporting to Markdown")
            markdown_text = result.document.export_to_markdown(page_break_placeholder="")
            (md_dir / f"{pdf_file.stem}.md").write_text(markdown_text, encoding='utf-8')

            logger.info("Saving tables")
            self.save_tables(markdown_text, tables_dir)
            del markdown_text # Explicitly free the large string

            logger.info("Saving images")
            self.save_page_images(result, images_dir)

            logger.info("Manual Cleanup")
            del result
            gc.collect() 

        except Exception as e:
            logger.exception(f"Error processing {pdf_file}")


    def run_pipeline(self, data_path: Path):
        # Move converter initialization outside the loop to reuse the engine
        # but clear the internal document cache each time.
        pipeline_options = PdfPipelineOptions()
        pipeline_options.images_scale = 2.0
        pipeline_options.generate_picture_images = True
        pipeline_options.generate_page_images = True

        doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

        pdf_files = list(data_path.rglob("*.pdf"))
        for pdf_file in pdf_files:
            logger.info(f"Processing: {pdf_file.name}")
            self.extract_pdf_content(pdf_file, doc_converter)
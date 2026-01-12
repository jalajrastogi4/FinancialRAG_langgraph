import base64
import io
from pathlib import Path
from PIL import Image
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from agents.llm import get_llm
from core.config import settings
from core.logging import get_logger
from prompts.image_prompt import describe_image_prompt

logger = get_logger()


class ImageDescription:
    def __init__(self):
        # self.llm = get_llm()
        self.model = get_llm()

    def generate_image_description(self, image_path: Path):
        image = Image.open(image_path)
        buffered = io.BytesIO()
        image.save(buffered, format='PNG')

        image_base64 = base64.b64encode(buffered.getvalue()).decode()

        message = HumanMessage(
            content=[
                {'type': 'text', 'text': describe_image_prompt},
                {'type': 'image_url', 'image_url': f'data:image/png;base64,{image_base64}'}
            ]
        )
        system_prompt = SystemMessage('You are an AI Assistant')
        response = self.model.invoke([system_prompt, message])
        return response.text

    def generate_and_save_description(self, image_path: Path):
        company_name = image_path.parent.parent.name
        doc_name = image_path.parent.name

        output_dir = Path(settings.OUTPUT_DESC_DIR)/company_name/doc_name
        output_dir.mkdir(parents=True, exist_ok=True)

        desc_file = output_dir / f"{image_path.stem}.md"

        if desc_file.exists():
            return False
        
        description = self.generate_image_description(image_path)
        desc_file.write_text(description, encoding='utf-8')
        
        return True

    def run_pipeline(self):
        images_path = Path(settings.OUTPUT_IMAGES_DIR)
        image_files = list(images_path.rglob("page_*.png"))

        for image_path in image_files:
            self.generate_and_save_description(image_path)
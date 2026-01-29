from docx import Document
from io import BytesIO

class WordViewerService:
    def generate_word_preview(self, file_storage, max_paragraphs=10):
        """从上传的 file_storage（Werkzeug FileStorage）读取 docx 内容并返回文本预览。

        返回：列表，每项为一段文本；如果文件类型不支持则抛出 ValueError。
        """
        filename = getattr(file_storage, 'filename', '') or ''
        if not filename.lower().endswith('.docx'):
            raise ValueError('only .docx files are supported')

        data = file_storage.read()
        if not data:
            raise ValueError('empty file')

        bio = BytesIO(data)
        try:
            doc = Document(bio)
        except Exception as e:
            raise ValueError(f'invalid docx file: {e}')

        paragraphs = []
        for p in doc.paragraphs:
            text = p.text.strip()
            if text:
                paragraphs.append(text)
            if len(paragraphs) >= max_paragraphs:
                break

        return paragraphs

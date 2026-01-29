import subprocess
import tempfile
import os
import shutil
from pathlib import Path
from io import BytesIO

class DocxService:
    def convert_to_pdf(self, file_storage, timeout: int = 30):
        """Convert an uploaded .docx FileStorage to PDF bytes using libreoffice (soffice).

        Returns (pdf_bytes, output_filename).
        Raises ValueError for bad input, RuntimeError if conversion tool is missing or conversion fails.
        """
        filename = getattr(file_storage, 'filename', '') or ''
        if not filename.lower().endswith('.docx'):
            raise ValueError('only .docx files are supported')

        # create temp dir
        tmpdir = Path(tempfile.mkdtemp(prefix='docx2pdf_'))
        try:
            in_path = tmpdir / Path(filename).name
            with in_path.open('wb') as f:
                data = file_storage.read()
                if not data:
                    raise ValueError('empty file')
                f.write(data)

            # locate soffice
            soffice_cmd = shutil.which('soffice') or shutil.which('libreoffice')
            if not soffice_cmd:
                raise RuntimeError('libreoffice (soffice) not found in PATH; please install LibreOffice')

            # run conversion
            # --headless --convert-to pdf --outdir <tmpdir> <in_path>
            try:
                subprocess.run([
                    soffice_cmd,
                    '--headless',
                    '--convert-to', 'pdf',
                    '--outdir', str(tmpdir),
                    str(in_path)
                ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
            except subprocess.CalledProcessError as cpe:
                raise RuntimeError(f'conversion failed: {cpe.stderr.decode(errors="ignore")}')

            out_path = in_path.with_suffix('.pdf')
            if not out_path.exists():
                raise RuntimeError('conversion completed but output PDF not found')

            pdf_bytes = out_path.read_bytes()
            out_name = out_path.name
            return pdf_bytes, out_name
        finally:
            # cleanup
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass

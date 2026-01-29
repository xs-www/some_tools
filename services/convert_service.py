import os
import subprocess
import time
import traceback

class ConvertService:
    def convert_docx_to_pdf(self, input_path: str, output_dir: str, pages: str = None) -> str:
        try:
            from docx2pdf import convert as d2p_convert
        except Exception:
            d2p_convert = None
        try:
            from pypdf import PdfReader, PdfWriter
        except Exception:
            PdfReader = PdfWriter = None

        base = os.path.splitext(os.path.basename(input_path))[0]
        out_path = os.path.join(output_dir, base + '.pdf')

        # 如果目标已存在，先删除以避免文件被锁定或写入冲突
        try:
            if os.path.exists(out_path):
                os.remove(out_path)
        except Exception:
            pass

        last_err = None
        # 尝试 docx2pdf（在独立 python 子进程中执行以隔离 COM/模块状态）
        if d2p_convert is not None:
            import sys
            for attempt in range(3):
                try:
                    cmd = [sys.executable, '-c', (
                        "from docx2pdf import convert; convert(\"%s\", \"%s\")" %
                        (input_path.replace('\\', '\\\\'), out_path.replace('\\', '\\\\'))
                    )]
                    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    if proc.returncode == 0 and os.path.exists(out_path):
                        # optionally cleanup WINWORD if configured
                        if os.name == 'nt' and os.environ.get('DOCX2PDF_CLEANUP_WINWORD') == '1':
                            try:
                                subprocess.run(['taskkill', '/IM', 'WINWORD.EXE', '/F'], capture_output=True)
                            except Exception:
                                pass
                        return out_path
                    else:
                        last_err = f"docx2pdf subprocess rc={proc.returncode} stdout={proc.stdout!r} stderr={proc.stderr!r}"
                except Exception:
                    last_err = traceback.format_exc()
                time.sleep(0.5)

        # 回退到 LibreOffice
        try:
            # 删除旧文件再调用 soffice
            try:
                if os.path.exists(out_path):
                    os.remove(out_path)
            except Exception:
                pass

            # 尝试定位 soffice：优先使用环境变量 SOFFICE_PATH，其次在 PATH 中查找
            import shutil
            soffice_exec = os.environ.get('SOFFICE_PATH') or shutil.which('soffice') or shutil.which('soffice.exe')
            # 如果仍未找到，尝试一些常见安装路径（Windows）
            if not soffice_exec and os.name == 'nt':
                common_paths = [
                    r"C:\Program Files\LibreOffice\program\soffice.exe",
                    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
                    r"C:\Program Files\OpenOffice\program\soffice.exe",
                    r"C:\Program Files (x86)\OpenOffice\program\soffice.exe",
                ]
                for p in common_paths:
                    if os.path.exists(p):
                        soffice_exec = p
                        break
            # 如果找到，确保它被记录（便于调试）
            if soffice_exec:
                try:
                    print(f"[ConvertService] using soffice at: {soffice_exec}")
                except Exception:
                    pass
            if not soffice_exec:
                last_err = (
                    'soffice executable not found. Install LibreOffice or set SOFFICE_PATH '
                    "(e.g. C:\\Program Files\\LibreOffice\\program\\soffice.exe)"
                )
            else:
                proc = subprocess.run([
                    soffice_exec, '--headless', '--convert-to', 'pdf', '--outdir', output_dir, input_path
                ], capture_output=True, text=True)
                if proc.returncode != 0:
                    last_err = f"soffice failed (rc={proc.returncode}): stdout={proc.stdout!r} stderr={proc.stderr!r}"
                else:
                    # success path: check file
                    if os.path.exists(out_path):
                        converted_path = out_path
        except Exception:
            last_err = traceback.format_exc()

        # 检查是否已生成 PDF
        if not os.path.exists(out_path):
            # include last error if available
            if last_err:
                raise Exception(f'conversion failed: {last_err}')
            else:
                raise Exception('conversion failed')

        converted_path = out_path

        # 如果用户指定了 pages，且 pypdf 可用，则提取指定页面到新 pdf
        if pages and PdfReader is not None and PdfWriter is not None:
            # pages 格式示例： "1-3,5,7-8"（1-based）
            def parse_ranges(s: str):
                parts = [p.strip() for p in s.split(',') if p.strip()]
                idxs = []
                for part in parts:
                    if '-' in part:
                        a, b = part.split('-', 1)
                        a = int(a); b = int(b)
                        idxs.extend(range(a - 1, b))
                    else:
                        idxs.append(int(part) - 1)
                # remove negatives and duplicates, keep order
                seen = set(); out = []
                for i in idxs:
                    if i < 0:
                        continue
                    if i not in seen:
                        seen.add(i); out.append(i)
                return out

            reader = PdfReader(converted_path)
            total = len(reader.pages)
            try:
                page_idxs = parse_ranges(pages)
            except Exception:
                raise Exception('invalid pages format')

            # clamp indexes
            page_idxs = [i for i in page_idxs if 0 <= i < total]
            if not page_idxs:
                raise Exception('no valid pages requested')

            writer = PdfWriter()
            for i in page_idxs:
                writer.add_page(reader.pages[i])

            sel_path = os.path.join(output_dir, os.path.splitext(os.path.basename(input_path))[0] + '_sel.pdf')
            with open(sel_path, 'wb') as f:
                writer.write(f)
            return sel_path

        return converted_path

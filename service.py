from mapper import UserDAO, ToolDAO, FavoriteDAO
from werkzeug.security import check_password_hash, generate_password_hash
import importlib
from datetime import datetime, timedelta
from config import BaseConfig

# 尝试导入 PyJWT，若所导入模块不提供 encode/decode，则回退到 itsdangerous
_jwt = None
try:
    _jwt = importlib.import_module('jwt')
    if not (hasattr(_jwt, 'encode') and hasattr(_jwt, 'decode')):
        _jwt = None
except Exception:
    _jwt = None

_ifallback = None
if _jwt is None:
    from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired
    _ifallback = {
        'Serializer': Serializer,
        'BadSignature': BadSignature,
        'SignatureExpired': SignatureExpired,
    }


class BaseService:
    """服务层基类。具体业务服务继承此类并实现所需方法。

    本文件不实现任何接口，仅提供结构和示例方法签名。
    """

    def __init__(self, db_session=None):
        self.db_session = db_session

    def get(self, *args, **kwargs):
        """示例：获取资源（未实现）"""
        raise NotImplementedError

    def create(self, *args, **kwargs):
        """示例：创建资源（未实现）"""
        raise NotImplementedError

    def update(self, *args, **kwargs):
        """示例：更新资源（未实现）"""
        raise NotImplementedError

    def delete(self, *args, **kwargs):
        """示例：删除资源（未实现）"""
        raise NotImplementedError


class AuthService(BaseService):
    """认证相关的业务服务（示例）。

    登录现在会返回 token，token 有效期基于配置（默认 15 天）。重复登录会刷新 token（返回新的 token）。
    """

    def _generate_token(self, username: str):
        secret = BaseConfig.JWT_SECRET
        if _jwt is not None:
            # 使用 PyJWT
            expires = datetime.utcnow() + timedelta(days=BaseConfig.JWT_EXPIRES_DAYS)
            payload = {
                'sub': username,
                'iat': datetime.utcnow().timestamp(),
                'exp': expires.timestamp(),
            }
            token = _jwt.encode(payload, secret, algorithm='HS256')
            if isinstance(token, bytes):
                token = token.decode('utf-8')
            return token
        else:
            # 使用 itsdangerous 回退实现（基于过期秒数）
            expires_seconds = int(86400 * BaseConfig.JWT_EXPIRES_DAYS)
            s = _ifallback['Serializer'](secret, expires_in=expires_seconds)
            token = s.dumps({'sub': username})
            if isinstance(token, bytes):
                token = token.decode('utf-8')
            return token

    def login(self, username: str, password: str):
        """登录逻辑：返回用户 dict（包含 token）或抛出 ValueError。"""
        if not username or not password:
            raise ValueError('username and password required')

        user = UserDAO.get_user_by_username(username)
        if not user:
            raise ValueError('invalid credentials')

        if not check_password_hash(user.hashed_password, password):
            raise ValueError('invalid credentials')

        token = self._generate_token(username)
        result = user.to_dict()
        result['token'] = token
        return result

    def register(self, username: str, password: str):
        """注册逻辑：使用新的 UserDAO 接口。"""
        if not username or not password:
            raise ValueError('username and password required')

        existing = UserDAO.get_user_by_username(username)
        if existing:
            raise ValueError('user already exists')

        hashed = generate_password_hash(password)
        user = UserDAO.create_user(username, hashed)
        return user.to_dict()

    def check_username_available(self, username: str) -> bool:
        """检查用户名是否可用，username 为空抛出 ValueError，返回 True 表示可用。"""
        if not username:
            raise ValueError('username required')
        existing = UserDAO.get_user_by_username(username)
        return existing is None

    def verify_token(self, token: str):
        secret = BaseConfig.JWT_SECRET
        if _jwt is not None:
            try:
                payload = _jwt.decode(token, secret, algorithms=['HS256'])
                return payload.get('sub')
            except Exception:
                return None
        else:
            try:
                s = _ifallback['Serializer'](secret)
                data = s.loads(token)
                return data.get('sub')
            except _ifallback['SignatureExpired']:
                return None
            except Exception:
                return None


class ToolService(BaseService):
    """工具相关业务：列出、获取、创建、删除工具（开发者权限）。"""

    def list_tools(self):
        return ToolDAO.list_tools()

    def get_tool(self, tool_id: int):
        t = ToolDAO.get_tool_by_id(tool_id)
        return t.to_dict() if t else None

    def create_tool(self, slug: str, title: str, description: str = None, route: str = None, icon: str = None, tags: str = None):
        tool = ToolDAO.create_tool(slug, title, description, route, icon, tags)
        return tool.to_dict()

    def delete_tool(self, tool_id: int):
        return ToolDAO.delete_tool(tool_id)


class FavoriteService(BaseService):
    """收藏相关业务。"""

    def list_user_favorites(self, username: str):
        user = UserDAO.get_user_by_username(username)
        if not user:
            raise ValueError('user not found')
        rows = FavoriteDAO.list_favorites_for_user(user.id)
        out = []
        for r in rows:
            tool = ToolDAO.get_tool_by_id(r['tool_id'])
            if tool:
                out.append({'tool': tool.to_dict(), 'created_at': r['created_at']})
        return out

    def add_favorite(self, username: str, tool_id: int):
        user = UserDAO.get_user_by_username(username)
        if not user:
            raise ValueError('user not found')
        tool = ToolDAO.get_tool_by_id(tool_id)
        if not tool:
            raise ValueError('tool not found')
        fav = FavoriteDAO.add_favorite(user.id, tool_id)
        return {'tool': tool.to_dict(), 'created_at': fav.created_at.isoformat()}

    def remove_favorite(self, username: str, tool_id: int):
        user = UserDAO.get_user_by_username(username)
        if not user:
            raise ValueError('user not found')
        ok = FavoriteDAO.remove_favorite(user.id, tool_id)
        return ok


class ConvertService(BaseService):
    """文档转换服务：提供将 Word 转为 PDF 的业务逻辑。

    优先使用 `docx2pdf`（Windows + MS Word），失败时回退到 LibreOffice 的 `soffice`。
    返回生成的 PDF 文件路径，若转换失败抛出 Exception。
    """

    def convert_docx_to_pdf(self, input_path: str, output_dir: str, pages: str = None) -> str:
        import os
        import subprocess
        import time
        import traceback
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
                    '(e.g. C:\\Program Files\\LibreOffice\\program\\soffice.exe)'
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
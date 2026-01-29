from controllers import bp_api, bp_ui
from flask import jsonify, request, render_template, send_file
import traceback
from services.wordviewer_service import WordViewerService
from services.docx_service import DocxService
from io import BytesIO
import base64

@bp_ui.route('/tools/word_viewer', methods=['GET'])
def word_viewer():
    """Word预览页面（示例）。"""
    return render_template('tools/word_viewer.html'), 200

@bp_api.route('/tools/word_viewer/pre_view', methods=['POST'])
def word_viewer_pre_view():
    """Word预览接口（示例）。"""
    try:
        file = request.files.get('file')
        if not file:
            return jsonify({'error': 'no file uploaded'}), 400

        # 调用 WordViewerService 进行处理
        result = WordViewerService().generate_word_preview(file)
        return jsonify({'preview': result}), 200
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500


@bp_api.route('/tools/word_viewer/docx_to_pdf', methods=['POST'])
def word_viewer_docx_to_pdf():
    """将上传的 docx 转为 pdf 并返回下载（或 base64）。"""
    try:
        file = request.files.get('file')
        as_download = request.form.get('download', '1') != '0'
        if not file:
            return jsonify({'error': 'no file uploaded'}), 400

        pdf_bytes, out_name = DocxService().convert_to_pdf(file)

        if as_download:
            return send_file(BytesIO(pdf_bytes), mimetype='application/pdf', download_name=out_name)
        else:
            b64 = base64.b64encode(pdf_bytes).decode('ascii')
            return jsonify({'filename': out_name, 'pdf_b64': b64}), 200
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except RuntimeError as re:
        return jsonify({'error': str(re)}), 503
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': 'internal error', 'detail': str(e)}), 500
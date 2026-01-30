from controllers import bp_api, bp_ui
from flask import jsonify, request, render_template
import os
import traceback
from services.convert_service import ConvertService

@bp_ui.route('/tools/docx_to_pdf', methods=['GET'])
def get_docx_to_pdf():
    return render_template('tools/docx_to_pdf.html'), 200

@bp_api.route('/tools/word_viewer/docx_to_pdf', methods=['POST'])
def convert_docx_to_pdf():
    docx_file = request.files.get('file')
    as_download = request.form.get('download', '1') != '0'
    if not docx_file:
        return jsonify({'error': 'no file uploaded'}), 400
    try:
        out_path, tmpdir = ConvertService().convert_docx_file(docx_file, pages=request.form.get('pages'))

        if not os.path.exists(out_path):
            return jsonify({'error': 'conversion failed, output missing'}), 500

        # NOTE: 返回后端文件地址（file_path）。
        # 重要：此处不立即删除临时目录，否则返回的路径将失效。请在外部或定期任务中清理 tmpdir。
        print("Conversion successful, output at:", out_path)
        return jsonify({'file_path': out_path}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

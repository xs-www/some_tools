function _getToken() {
  try {
    return localStorage.getItem('token') || (function(){
      // 从 cookie 回退
      const m = document.cookie.match(/(?:^|; )token=([^;]+)/);
      return m ? decodeURIComponent(m[1]) : null;
    })();
  } catch (e) {
    return null;
  }
}

async function convertDocxToPdf(file, asDownload = true) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('download', asDownload ? '1' : '0');

  const token = _getToken();
  const headers = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const resp = await fetch('/api/tools/word_viewer/docx_to_pdf', {
    method: 'POST',
    headers,
    body: formData
  });
  if (!resp.ok) {
    const err = await resp.json().catch(()=>({error:'non-json response'}));
    throw new Error(err.error || 'conversion failed');
  }

  if (asDownload) {
    // trigger browser download
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    // attempt to get filename from Content-Disposition
    const cd = resp.headers.get('Content-Disposition') || '';
    let filename = 'converted.pdf';
    const m = cd.match(/filename\*=UTF-8''(.+)$|filename="?([^";]+)"?/);
    if (m) filename = decodeURIComponent(m[1] || m[2]);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    return {downloaded: true};
  } else {
    const data = await resp.json();
    return data; // { filename, pdf_b64 }
  }
}

// helper to wire input and buttons
function setupDocxToPdfForm(formId) {
  const form = document.getElementById(formId);
  if (!form) return;
  const input = form.querySelector('input[type=file]');
  const preview = form.querySelector('.preview');
  const downloadBtn = form.querySelector('.download');
  const previewBtn = form.querySelector('.preview-btn');

  downloadBtn && downloadBtn.addEventListener('click', async (ev) => {
    ev.preventDefault();
    if (!input.files.length) return alert('请选择 docx 文件');
    try {
      await convertDocxToPdf(input.files[0], true);
    } catch (e) {
      alert(e.message);
    }
  });

  previewBtn && previewBtn.addEventListener('click', async (ev) => {
    ev.preventDefault();
    if (!input.files.length) return alert('请选择 docx 文件');
    try {
      const res = await convertDocxToPdf(input.files[0], false);
      if (res && res.pdf_b64) {
        const iframe = document.createElement('iframe');
        iframe.src = 'data:application/pdf;base64,' + res.pdf_b64;
        iframe.width = '100%';
        iframe.height = '600px';
        preview.innerHTML = '';
        preview.appendChild(iframe);
      } else {
        preview.innerText = '无法预览';
      }
    } catch (e) {
      alert(e.message);
    }
  });
}

// auto-setup forms with class
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('form.docx-to-pdf').forEach(f => {
    // prefer id, fallback to dataset.formId
    const id = f.id || f.dataset.formId;
    if (id) setupDocxToPdfForm(id);
  });
});

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

// Progress helpers
function _findProgress(form) {
  if (!form) return null;
  return form.querySelector('.convert-progress');
}
function showProgress(form, text) {
  const p = _findProgress(form);
  if (!p) return;
  p.style.display = '';
  const txt = p.querySelector('.progress-text');
  if (txt) txt.textContent = text || '处理中...';
  const fill = p.querySelector('.progress-fill');
  if (fill) fill.style.width = '0%';
}
function updateProgress(form, percent, text) {
  const p = _findProgress(form);
  if (!p) return;
  const fill = p.querySelector('.progress-fill');
  if (fill) fill.style.width = Math.max(0, Math.min(100, percent)) + '%';
  const txt = p.querySelector('.progress-text');
  if (txt && text) txt.textContent = text;
}
function hideProgress(form) {
  const p = _findProgress(form);
  if (!p) return;
  p.style.display = 'none';
}

async function convertDocxToPdf(file, asDownload = true, formElement = null) {
  console.debug('[docx_to_pdf] convertDocxToPdf called', { fileName: file && file.name, asDownload });
  if (!file) throw new Error('no file provided');
  const fd = new FormData();
  fd.append('file', file);
  fd.append('download', asDownload ? '1' : '0');
  const pagesEl = document.getElementById('pages-input');
  if (pagesEl && pagesEl.value) fd.append('pages', pagesEl.value);

  const token = _getToken();

  // show progress UI if available
  if (formElement) showProgress(formElement, '开始上传...');

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/tools/word_viewer/docx_to_pdf', true);
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);

    xhr.responseType = 'blob';

    xhr.upload.onprogress = function (ev) {
      if (ev.lengthComputable) {
        const pct = Math.round((ev.loaded / ev.total) * 50); // 上传占总进度的前 50%
        updateProgress(formElement, pct, `上传中 ${pct}%`);
      } else {
        updateProgress(formElement, 10, '上传中...');
      }
    };

    xhr.onprogress = function (ev) {
      // 下载/转换阶段，占后 50%
      if (ev.lengthComputable) {
        const pct = 50 + Math.round((ev.loaded / ev.total) * 50);
        updateProgress(formElement, pct, `下载中 ${pct}%`);
      } else {
        updateProgress(formElement, 70, '转换中...');
      }
    };

    xhr.onload = function () {
      try {
        if (xhr.status < 200 || xhr.status >= 300) {
          // try to parse json error from response
          let text = '';
          try { text = xhr.response ? new TextDecoder().decode(xhr.response) : ''; } catch (e) { text = ''; }
          hideProgress(formElement);
          return reject(new Error('conversion failed: ' + (text || xhr.status)));
        }

        const contentType = (xhr.getResponseHeader('content-type') || '').toLowerCase();
        if (contentType.includes('application/pdf')) {
          const blob = xhr.response;
          // try to get filename
          const cd = xhr.getResponseHeader('Content-Disposition') || '';
          let filename = 'converted.pdf';
          const m = cd.match(/filename\*=UTF-8''(.+)$|filename=?"?([^";]+)"?/);
          if (m) filename = decodeURIComponent(m[1] || m[2]);

          hideProgress(formElement);
          if (asDownload) {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            setTimeout(() => { try { URL.revokeObjectURL(url); } catch (e) {} }, 30000);
            return resolve({downloaded: true});
          } else {
            const url = URL.createObjectURL(blob);
            return resolve({pdf_blob_url: url, filename});
          }
        }

        // otherwise assume JSON returned
        const reader = new FileReader();
        reader.onload = () => {
          hideProgress(formElement);
          try {
            const text = reader.result;
            const json = JSON.parse(text);
            resolve(json);
          } catch (e) {
            reject(new Error('failed to parse response'));
          }
        };
        reader.onerror = () => { hideProgress(formElement); reject(new Error('failed to read response')); };
        reader.readAsText(xhr.response);
      } catch (e) {
        hideProgress(formElement);
        reject(e);
      }
    };

    xhr.onerror = function (ev) { hideProgress(formElement); reject(new Error('network error')); };

    xhr.send(fd);
  });
}

// helper to render returned file_path or other metadata into the UI
function showFileResult(container, data) {
  // container: element where to show result
  if (!container) return;
  // ensure preview-area (wrapper) is visible
  const previewWrapper = container.closest('#preview-area') || document.getElementById('preview-area');
  if (previewWrapper) previewWrapper.style.display = '';

  // remove existing result
  let resArea = container.querySelector('.file-result');
  if (!resArea) {
    resArea = document.createElement('div');
    resArea.className = 'file-result';
    resArea.style.marginTop = '12px';
    container.appendChild(resArea);
  }
  resArea.innerHTML = '';

  if (!data) {
    resArea.textContent = '无返回数据';
    return;
  }

  if (data.pdf_b64) {
    const iframe = document.createElement('iframe');
    iframe.src = 'data:application/pdf;base64,' + data.pdf_b64;
    iframe.width = '100%';
    iframe.height = '600px';
    resArea.appendChild(iframe);
    return;
  }

  if (data.file_path) {
    const p = document.createElement('div');
    p.textContent = '服务器文件路径： ' + data.file_path;
    p.style.wordBreak = 'break-all';
    resArea.appendChild(p);

    // Use POST proxy to fetch blob and embed into iframe for preview
    const legacyFrame = document.getElementById('preview-frame');
    const previewWrapper = document.getElementById('preview-area');
    if (previewWrapper) previewWrapper.style.display = '';

    const embedBlob = async (deleteFlag = '0', openInNew = false) => {
      const blob = await fetchProxyFile(data.file_path, deleteFlag);
      if (!(blob instanceof Blob)) {
        // unexpected response
        throw new Error('proxy did not return PDF blob');
      }
      const url = URL.createObjectURL(blob);
      if (legacyFrame) {
        legacyFrame.src = url;
      } else {
        const iframe = document.createElement('iframe');
        iframe.src = url;
        iframe.width = '100%';
        iframe.height = '600px';
        iframe.style.marginTop = '8px';
        resArea.appendChild(iframe);
      }
      if (openInNew) {
        window.open(url, '_blank');
      }
      // revoke URL after a while to free memory
      setTimeout(() => { try { URL.revokeObjectURL(url); } catch (e) {} }, 60 * 1000);
    };

    const btns = document.createElement('div');
    btns.style.marginTop = '8px';
    btns.style.display = 'flex';
    btns.style.gap = '8px';

    const makeOpen = (fn) => fn;

    const btnDownload = document.createElement('button');
    btnDownload.textContent = '下载 (保留)';
    btnDownload.className = 'btn';
    btnDownload.addEventListener('click', async () => {
      try {
        await embedBlob('0', true);
      } catch (e) { alert('下载失败: ' + e.message); }
    });

    const btnDownloadRemove = document.createElement('button');
    btnDownloadRemove.textContent = '下载并删除';
    btnDownloadRemove.className = 'btn';
    btnDownloadRemove.addEventListener('click', async () => {
      try {
        await embedBlob('1', true);
      } catch (e) { alert('下载失败: ' + e.message); }
    });

    const btnOpen = document.createElement('button');
    btnOpen.textContent = '在新标签打开代理链接';
    btnOpen.className = 'btn';
    btnOpen.addEventListener('click', async () => {
      try {
        await embedBlob('0', true);
      } catch (e) { alert('下载失败: ' + e.message); }
    });

    btns.appendChild(btnDownload);
    btns.appendChild(btnDownloadRemove);
    btns.appendChild(btnOpen);
    resArea.appendChild(btns);
    return;
  }

  // fallback: show raw JSON
  const pre = document.createElement('pre');
  pre.textContent = JSON.stringify(data, null, 2);
  resArea.appendChild(pre);
}

// helper to wire input and buttons
function setupDocxToPdfForm(formId) {
  const form = document.getElementById(formId);
  if (!form) return;
  const input = form.querySelector('input[type=file]');
  let preview = form.querySelector('.preview');
  if (!preview) {
    // fallback: allow preview container outside the form
    preview = document.querySelector('.preview') || document.getElementById('preview-area') || null;
    // if preview is the wrapper (#preview-area) and does not have inner container, create one
    if (preview && !preview.classList.contains('preview')) {
      // make sure we have a child container to insert iframe into
      let inner = preview.querySelector('.preview');
      if (!inner) {
        inner = document.createElement('div');
        inner.className = 'preview';
        preview.appendChild(inner);
      }
      preview = inner;
    }
  }
  const downloadBtn = form.querySelector('.download');
  const previewBtn = form.querySelector('.preview-btn');

  // define handlers so we can attach either directly or via delegation
  const _downloadHandler = async (ev) => {
    ev.preventDefault();
    if (!input.files.length) return alert('请选择 docx 文件');
    try {
      const res = await convertDocxToPdf(input.files[0], true, form);
      // if backend returned metadata instead of direct PDF, show it
      if (res && res.file_path) {
        showFileResult(preview || document.body, res);
      }
      // if downloaded in-browser, nothing more to do
    } catch (e) {
      alert(e.message);
    }
  };

  const _previewHandler = async (ev) => {
    ev.preventDefault();
    console.debug('[docx_to_pdf] preview button clicked');
    if (!input.files.length) return alert('请选择 docx 文件');
    // open a blank window immediately to avoid popup blockers
    let win = null;
    try { win = window.open('', '_blank'); } catch (e) { win = null; }
    try {
      const res = await convertDocxToPdf(input.files[0], false, form);
      // If server returned base64 PDF
      if (res && res.pdf_b64) {
        // convert base64 to blob
        try {
          const byteChars = atob(res.pdf_b64);
          const byteNumbers = new Array(byteChars.length);
          for (let i = 0; i < byteChars.length; i++) {
            byteNumbers[i] = byteChars.charCodeAt(i);
          }
          const byteArray = new Uint8Array(byteNumbers);
          const blob = new Blob([byteArray], { type: 'application/pdf' });
          const url = URL.createObjectURL(blob);
          if (win) { win.location.href = url; } else { window.open(url, '_blank'); }
          setTimeout(() => { try { URL.revokeObjectURL(url); } catch (e) {} }, 60 * 1000);
          return;
        } catch (e) {
          console.error(e);
          if (win) try { win.close(); } catch (e) {}
          alert('无法解码后端返回的 PDF');
          return;
        }
      } else if (res && res.pdf_blob_url) {
        if (win) { win.location.href = res.pdf_blob_url; } else { window.open(res.pdf_blob_url, '_blank'); }
        setTimeout(() => { try { URL.revokeObjectURL(res.pdf_blob_url); } catch (e) {} }, 30000);
        return;
      } else if (res && res.file_path) {
        // try to fetch proxy blob and open in new tab
        try {
          const blob = await fetchProxyFile(res.file_path, '0');
          const url = URL.createObjectURL(blob);
          if (win) { win.location.href = url; } else { window.open(url, '_blank'); }
          setTimeout(() => { try { URL.revokeObjectURL(url); } catch (e) {} }, 60 * 1000);
          return;
        } catch (e) {
          console.error('proxy fetch failed', e);
          if (win) try { win.close(); } catch (e) {}
          // fallback: show controls in page
          showFileResult(preview || document.body, res);
          return;
        }
      } else {
        if (win) try { win.close(); } catch (e) {}
        alert('后端未返回可预览的 PDF 数据');
      }
    } catch (e) {
      if (win) try { win.close(); } catch (e) {}
      alert(e.message);
    }
  };

  // attach handlers: prefer direct binding to specific buttons, otherwise fallback to delegation on the form
  if (downloadBtn) {
    downloadBtn.addEventListener('click', _downloadHandler);
    console.debug('[docx_to_pdf] download button bound');
  } else {
    form.addEventListener('click', (ev) => {
      if (ev.target && ev.target.matches && ev.target.matches('.download')) _downloadHandler(ev);
    });
    console.debug('[docx_to_pdf] download delegated to form');
  }

  if (previewBtn) {
    previewBtn.addEventListener('click', _previewHandler);
    console.debug('[docx_to_pdf] preview button bound');
  } else {
    form.addEventListener('click', (ev) => {
      if (ev.target && ev.target.matches && ev.target.matches('.preview-btn')) _previewHandler(ev);
    });
    console.debug('[docx_to_pdf] preview delegated to form');
  }
}

// helper to fetch server temp file via POST proxy and return Blob
async function fetchProxyFile(path, deleteFlag = '0') {
  if (!path) throw new Error('no path provided');
  const token = _getToken();
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const resp = await fetch('/api/download_temp', {
    method: 'POST',
    headers,
    body: JSON.stringify({ path, delete: deleteFlag })
  });
  if (!resp.ok) {
    const err = await resp.json().catch(()=>({ error: 'non-json response' }));
    throw new Error(err.error || ('proxy failed: ' + resp.status));
  }
  const ct = (resp.headers.get('content-type') || '').toLowerCase();
  if (ct.includes('application/pdf')) {
    return await resp.blob();
  }
  // if not pdf, try to parse json error
  const data = await resp.json().catch(()=>null);
  throw new Error((data && data.error) ? data.error : 'unexpected proxy response');
}

// Auto-initialize any forms with class 'docx-to-pdf'
function _initDocxToPdfForms() {
  try {
    const forms = Array.from(document.querySelectorAll('form.docx-to-pdf'));
    if (!forms.length) {
      console.debug('[docx_to_pdf] no forms with .docx-to-pdf found to initialize');
      return;
    }
    forms.forEach((f, idx) => {
      if (!f.id) f.id = `docx-to-pdf-auto-${idx}`;
      try {
        setupDocxToPdfForm(f.id);
        console.debug('[docx_to_pdf] initialized form', { id: f.id });
      } catch (e) {
        console.error('[docx_to_pdf] failed to initialize form', { id: f.id, error: e });
      }
    });
  } catch (e) {
    console.error('[docx_to_pdf] auto-init error', e);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', _initDocxToPdfForms);
} else {
  // DOM already ready — initialize immediately
  _initDocxToPdfForms();
}

// end of file

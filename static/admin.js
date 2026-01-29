document.addEventListener('DOMContentLoaded', function(){
  async function apiFetch(path, opts={}){
    const token = localStorage.getItem('token')
    const headers = opts.headers || {'Content-Type':'application/json'}
    if(token) headers['Authorization'] = 'Bearer ' + token
    const res = await fetch('/api' + path, Object.assign({headers}, opts))
    try{ return await res.json() }catch(e){ return {error:'invalid json response'} }
  }

  function showFormMsg(text){ document.getElementById('form-msg').textContent = text }

  let currentEditing = null // slug of tool being edited

  function setEditMode(slug){
    currentEditing = slug
    const heading = document.getElementById('form-heading')
    if(heading) heading.textContent = slug ? '编辑工具' : '注册新工具'
  }

  async function refresh(){
    const d = await apiFetch('/admin/tools', {method:'GET'})
    const container = document.getElementById('tool-list')
    if(!container) return
    container.innerHTML = ''
    const statsTagEl = document.getElementById('stat-by-tag')
    const statTotalEl = document.getElementById('stat-total')

    if(d && d.tools && Array.isArray(d.tools)){
      // compute stats
      const total = d.tools.length
      const tagCounts = {}
      d.tools.forEach(t => {
        const tags = (t.tags || '')
          .split(',')
          .map(s => s.trim().toLowerCase())
          .filter(Boolean)
        if(tags.length === 0){
          tagCounts['(none)'] = (tagCounts['(none)'] || 0) + 1
        }
        tags.forEach(tag => { tagCounts[tag] = (tagCounts[tag] || 0) + 1 })
      })

      if(statTotalEl) statTotalEl.textContent = '总工具: ' + total
      if(statsTagEl){
        statsTagEl.innerHTML = ''
        const ul = document.createElement('div')
        for(const [tag, cnt] of Object.entries(tagCounts)){
          const row = document.createElement('div')
          row.textContent = tag + ': ' + cnt
          ul.appendChild(row)
        }
        statsTagEl.appendChild(ul)
      }

      d.tools.forEach(t=>{
        const row = document.createElement('div')
        row.className = 'tool-row'
        row.style.display = 'flex'
        row.style.justifyContent = 'space-between'
        row.style.alignItems = 'center'
        row.style.padding = '6px 0'

        const left = document.createElement('div')
        left.textContent = t.title + ' (' + t.slug + ') — ' + (t.route || '')

        const right = document.createElement('div')

        const btnEdit = document.createElement('button')
        btnEdit.textContent = '编辑'
        btnEdit.addEventListener('click', ()=>{
          // populate form
          setEditMode(t.slug)
          document.getElementById('input-slug').value = t.slug
          document.getElementById('input-title').value = t.title
          document.getElementById('input-description').value = t.description || ''
          document.getElementById('input-route').value = t.route || ''
          document.getElementById('input-icon').value = t.icon || ''
          document.getElementById('input-tags').value = t.tags || ''
          showFormMsg('编辑模式：修改后点击提交。')
        })

        right.appendChild(btnEdit)
        row.appendChild(left)
        row.appendChild(right)
        container.appendChild(row)
      })
    } else if(d && d.error){
      if(statTotalEl) statTotalEl.textContent = '总工具: 0'
      if(statsTagEl) statsTagEl.textContent = '获取失败: ' + d.error
      container.textContent = '获取失败: ' + d.error
    }
  }

  const btnRefresh = document.getElementById('btn-refresh')
  if(btnRefresh) btnRefresh.addEventListener('click', refresh)

  const btnClear = document.getElementById('btn-clear')
  if(btnClear) btnClear.addEventListener('click', ()=>{
    setEditMode(null)
    const form = document.getElementById('tool-form')
    if(form) form.reset()
    showFormMsg('')
  })

  async function submitCreateOrUpdate(payload){
    if(currentEditing){
      // PUT to update
      const r = await apiFetch('/admin/tools/' + encodeURIComponent(currentEditing), {method:'PUT', body: JSON.stringify(payload)})
      return r
    }else{
      // POST to create
      const r = await apiFetch('/admin/tools', {method:'POST', body: JSON.stringify(payload)})
      return r
    }
  }

  const form = document.getElementById('tool-form')
  if(form){
    form.addEventListener('submit', async (e)=>{
      e.preventDefault()
      showFormMsg('')
      const slug = document.getElementById('input-slug').value.trim()
      const title = document.getElementById('input-title').value.trim()
      if(!slug || !title){ showFormMsg('slug 和 title 为必填'); return }
      const payload = {
        slug,
        title,
        description: document.getElementById('input-description').value.trim() || undefined,
        route: document.getElementById('input-route').value.trim() || undefined,
        icon: document.getElementById('input-icon').value.trim() || undefined,
        tags: document.getElementById('input-tags').value.trim() || undefined,
      }
      const r = await submitCreateOrUpdate(payload)
      if(r && r.tool){
        showFormMsg(currentEditing ? '更新成功' : '创建成功')
        form.reset()
        setEditMode(null)
        currentEditing = null
        refresh()
      }else if(r && r.error){
        showFormMsg((r && r.error) || '操作失败')
      }else{
        showFormMsg('操作失败')
      }
    })
  }

  // 初始化
  refresh()
})

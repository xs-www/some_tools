const API_BASE = (window.API_BASE || 'http://localhost:8080') + '/api'

// 延迟初始化这些依赖 DOM 的变量
let formArea, msgEl, tabLogin, tabRegister

function showMessage(text, type='success'){
  msgEl.innerHTML = `<div class="msg ${type}">${text}</div>`
}

function clearMessage(){ msgEl.innerHTML = '' }

function renderLogin(){
  tabLogin.classList.add('active')
  tabRegister.classList.remove('active')
  formArea.innerHTML = `
    <label>用户名</label>
    <input id="username" type="text" />
    <label>密码</label>
    <input id="password" type="password" />
    <div class="actions">
      <button id="btn-login">登录</button>
    </div>
  `
  document.getElementById('btn-login').addEventListener('click', doLogin)
}

function openModal(html){
  const modal = document.createElement('div')
  modal.style.position = 'fixed'
  modal.style.left = 0
  modal.style.top = 0
  modal.style.right = 0
  modal.style.bottom = 0
  modal.style.background = 'rgba(0,0,0,0.4)'
  modal.style.display = 'flex'
  modal.style.alignItems = 'center'
  modal.style.justifyContent = 'center'
  modal.innerHTML = `<div style="background:#fff;padding:20px;border-radius:8px;max-width:420px;width:100%">${html}</div>`
  document.body.appendChild(modal)
  return modal
}

async function checkUsernameRemote(username){
  try{
    const res = await fetch(API_BASE + '/check_username', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username})})
    const d = await res.json()
    return {ok: res.ok, data: d}
  }catch(e){ return {ok:false, error: e.message} }
}

function renderRegister(){
  // 打开弹窗第一步：输入用户名
  const modal = openModal(`
    <h3>注册 - 步骤 1/2</h3>
    <label>用户名</label>
    <input id="modal-username" type="text" />
    <div style="margin-top:12px;display:flex;gap:8px;justify-content:flex-end">
      <button id="modal-cancel">取消</button>
      <button id="modal-next">下一步</button>
    </div>
    <div id="modal-msg"></div>
  `)

  modal.querySelector('#modal-cancel').addEventListener('click', ()=> modal.remove())
  modal.querySelector('#modal-next').addEventListener('click', async ()=>{
    const username = document.getElementById('modal-username').value.trim()
    const msg = modal.querySelector('#modal-msg')
    msg.innerText = ''
    if(!username){ msg.innerText = '用户名为必填'; return }
    msg.innerText = '校验中...'
    const r = await checkUsernameRemote(username)
    if(!r.ok){ msg.innerText = r.error || '校验失败'; return }
    if(r.data && r.data.available){
      // 关闭当前 modal，打开第二步
      modal.remove()
      openRegisterStep2(username)
    }else{
      msg.innerText = '用户名已存在，请更换'
    }
  })
}

function openRegisterStep2(username){
  const modal = openModal(`
    <h3>注册 - 步骤 2/2</h3>
    <p>用户名：${username}</p>
    <label>密码</label>
    <input id="modal-pass1" type="password" />
    <label>再次输入密码</label>
    <input id="modal-pass2" type="password" />
    <div style="margin-top:12px;display:flex;gap:8px;justify-content:flex-end">
      <button id="modal-cancel">取消</button>
      <button id="modal-submit">提交</button>
    </div>
    <div id="modal-msg"></div>
  `)

  modal.querySelector('#modal-cancel').addEventListener('click', ()=> modal.remove())
  modal.querySelector('#modal-submit').addEventListener('click', async ()=>{
    const p1 = document.getElementById('modal-pass1').value
    const p2 = document.getElementById('modal-pass2').value
    const msg = modal.querySelector('#modal-msg')
    msg.innerText = ''
    if(!p1 || !p2){ msg.innerText = '请填写两次密码'; return }
    if(p1 !== p2){ msg.innerText = '两次输入密码不一致'; return }
    // 调用注册 API
    const r = await doFetch('/register', {username, password: p1})
    if(r.ok){
      modal.remove()
      showMessage('注册成功，请登录')
      renderLogin()
    }else{
      msg.innerText = r.data && r.data.error ? r.data.error : (r.error || '注册失败')
    }
  })
}

async function doFetch(path, payload){
  clearMessage()
  try{
    // 自动从 localStorage 读取 token 并加入请求头（若存在）
    const token = localStorage.getItem('token')
    const headers = {'Content-Type':'application/json'}
    if (token) headers['Authorization'] = 'Bearer ' + token

    const res = await fetch(API_BASE + path, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(payload),
    })
    const data = await res.json()
    if (res.ok) return {ok:true, data}
    return {ok:false, status: res.status, data}
  }catch(e){
    return {ok:false, error: e.message}
  }
}

async function doLogin(ev){
  ev && ev.preventDefault()
  const username = document.getElementById('username').value.trim()
  const password = document.getElementById('password').value
  if(!username || !password){ showMessage('用户名和密码为必填', 'error'); return }

  const r = await doFetch('/login', {username, password})
  if(r.ok){
    // 若后端返回 token，则保存到 localStorage
    const token = r.data && r.data.token
    if (token) localStorage.setItem('token', token)
    // 保存用户信息（如果后端返回）
    const user = r.data && r.data.user
    if (user) localStorage.setItem('user', JSON.stringify(user))
    showMessage('登录成功')
    // 跳转到用户主页（延迟以便显示成功信息）
    setTimeout(()=>{ try{ showHome() }catch(e){ console.error(e) } }, 300)
  }
  else{
    const text = r.data && r.data.error ? r.data.error : (r.error || '请求失败')
    showMessage('用户名或密码错误', 'error')
  }
}

function showHome(){
  // 重定向到服务器渲染的主页路由
  window.location.href = '/ui/home'
}

function initHomeUI(){
  const avatar = document.getElementById('avatar')
  const profileName = document.getElementById('profile-username')
  if (!avatar && !profileName) return
  const userStr = localStorage.getItem('user')
  const user = userStr ? JSON.parse(userStr) : {username: 'User'}
  const uname = user.username || 'User'
  const initials = uname.slice(0,2).toUpperCase()
  if(avatar) avatar.textContent = initials
  if(profileName) profileName.textContent = uname

  // 绑定侧栏切换
  document.querySelectorAll('.nav-item').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      document.querySelectorAll('.nav-item').forEach(b=>b.classList.remove('active'))
      btn.classList.add('active')
      const tab = btn.getAttribute('data-tab')
      document.querySelectorAll('.tab-content').forEach(tc=>tc.classList.remove('active'))
      const el = document.getElementById('tab-' + tab)
      if(el) el.classList.add('active')
    })
  })
}

// 修改原来触发注册的按钮绑定
function attachRegisterTrigger(){
  // 如果页面上有原 register 按钮则保留弹窗逻辑
  const regBtn = document.getElementById('btn-register')
  if(regBtn){
    regBtn.removeEventListener('click', doRegister)
    regBtn.addEventListener('click', (e)=>{ e && e.preventDefault(); renderRegister() })
  }
}

// 初始渲染和事件绑定，等待 DOM 完全加载
document.addEventListener('DOMContentLoaded', function(){
  formArea = document.getElementById('form-area')
  msgEl = document.getElementById('message')
  tabLogin = document.getElementById('tab-login')
  tabRegister = document.getElementById('tab-register')

  if (tabLogin) tabLogin.addEventListener('click', renderLogin)
  if (tabRegister) tabRegister.addEventListener('click', renderRegister)

  // 仅当存在登录表单容器时才初始化登录页相关逻辑
  if (formArea) {
    renderLogin()
    setTimeout(attachRegisterTrigger, 100)
  }

  // 如果当前页面是主页（模板渲染后包含 avatar），初始化主页交互
  try{ initHomeUI() }catch(e){ /* ignore */ }
})

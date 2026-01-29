// home page script: logout and init hook
// Assumes app.js defines initHomeUI()
(function(){
  // 登出按钮行为：清空本地存储的 token/user 并跳转到登录页
  function attachLogout(){
    var btn = document.getElementById('btn-logout')
    if(!btn) return
    btn.addEventListener('click', function(){
      try{ localStorage.removeItem('token'); localStorage.removeItem('user'); }catch(e){}
      window.location.href = '/login'
    })
  }

  function init(){
    attachLogout()
    try{ initHomeUI() }catch(e){ /* ignore if app.js not loaded */ }
  }

  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', init)
  } else {
    init()
  }
})()

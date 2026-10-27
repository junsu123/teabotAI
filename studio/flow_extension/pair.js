// Only an explicit local pairing tab created by Mars Studio can bind a profile.
(() => {
  if (location.hostname !== '127.0.0.1' || location.pathname !== '/flow-extension-pair') return;
  const params = new URLSearchParams(location.search);
  const id = params.get('id'), token = params.get('token');
  if (!/^[a-f0-9]{32}$/.test(id || '') || !/^[a-f0-9]{32}$/.test(token || '')) return;
  chrome.runtime.sendMessage({kind:'pair',id,token,port:location.port}, response => {
    const box = document.querySelector('#pairStatus');
    if (box) box.textContent = response?.ok
      ? 'Đã ghép tiện ích với profile này. Quay về Google Flow để đăng nhập.'
      : 'Chưa ghép thành công. Hãy kiểm tra tiện ích rồi tải lại trang.';
  });
})();

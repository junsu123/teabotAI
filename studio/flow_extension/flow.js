// A narrow, read-only content script. NO cookies, tokens, localStorage or requests.
(() => {
  if (!['flow.google.com','labs.google'].includes(location.hostname)) return;
  let delivered=false, lastSignature='';
  function inspect() {
    if (delivered) return;
    const panel=document.querySelector('flow-account-panel, .flow-account-panel, .account-panel');
    const root=panel || document;
    const email=(root.querySelector('.user-email')?.textContent||'').trim();
    const creditText=(root.querySelector('.credits-count')?.textContent||'').trim();
    if (!/^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/.test(email)) return;
    const match=creditText.match(/^(\d{1,3}(?:[., ]\d{3})+|\d{1,7})(?![\d.,])/);
    if (!match || !/(?:tín\s*dụng|credits?|google\s*flow)/i.test(creditText)) return;
    const credits=Number(match[1].replace(/[., ]/g,''));
    if (!Number.isSafeInteger(credits) || credits<0 || credits>1000000) return;
    const signature=email+'|'+credits;
    if (signature===lastSignature) return;
    lastSignature=signature;
    chrome.runtime.sendMessage({kind:'capture',email,credits}, response=>{
      if (response?.ok) delivered=true;
      else lastSignature='';
    });
  }
  const observer=new MutationObserver(()=>inspect());
  observer.observe(document.documentElement,{childList:true,subtree:true,characterData:true});
  inspect();
  // Service worker might not yet be paired; keep checking until it is.
  setInterval(inspect,4000);
})();

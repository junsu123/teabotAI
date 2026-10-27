// Browser-owned credentials are untouched. Only email and integer credits leave Flow.
const PAIR_KEY='marsFlowPair';
chrome.runtime.onMessage.addListener((message,sender,sendResponse)=>{
  (async()=>{
    if(message?.kind==='pair') {
      const url=new URL(sender.url||'');
      if(url.protocol!=='http:' || url.hostname!=='127.0.0.1' ||
         url.pathname!=='/flow-extension-pair' ||
         !/^[a-f0-9]{32}$/.test(message.id||'') ||
         !/^[a-f0-9]{32}$/.test(message.token||'') ||
         !/^\d{2,5}$/.test(message.port||'')) return {ok:false};
      await chrome.storage.local.set({[PAIR_KEY]:{id:message.id,token:message.token,port:message.port}});
      return {ok:true};
    }
    if(message?.kind==='capture') {
      const host=new URL(sender.url||'').hostname;
      if(!['flow.google.com','labs.google'].includes(host)) return {ok:false};
      const { [PAIR_KEY]:binding }=await chrome.storage.local.get(PAIR_KEY);
      if(!binding || !/^[a-f0-9]{32}$/.test(binding.id)) return {ok:false};
      if(typeof message.email!=='string' || !Number.isSafeInteger(message.credits)) return {ok:false};
      const endpoint='http://127.0.0.1:'+binding.port+'/api/flow/enrollments/capture';
      const response=await fetch(endpoint,{method:'POST',headers:{
        'Content-Type':'application/json','X-Tea-Flow-Extension':'1'
      },body:JSON.stringify({id:binding.id,token:binding.token,
                              email:message.email,credits:message.credits})});
      const result=await response.json();
      if(!response.ok || !result.ok) return {ok:false};
      await chrome.storage.local.remove(PAIR_KEY);
      // The extension explicitly closes its own Flow window after the local
      // dashboard has durably persisted the account. No process kill or bypass.
      if(typeof sender.tab?.windowId==='number')
        await chrome.windows.remove(sender.tab.windowId);
      return {ok:true};
    }
    return {ok:false};
  })().then(sendResponse).catch(()=>sendResponse({ok:false}));
  return true;
});

/* TEA AI Mars Studio GUI. All mutations are initiated explicitly by the user. */
const h = x => String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const $ = s => document.querySelector(s);
let data={agents:[],accounts:[],jobs:[],missions:[],learnings:[],products:{},proxies:[],training:[],stats:{}}, activeView='hq', focusAgent=null, sceneScale=1, sceneMode='mars';
let forumMissionId=0,forumData=null,forumBusy=false;
const labels={hq:'Trụ sở AI',agents:'Nhân viên AI',missions:'Giao nhiệm vụ CEO',forum:'Phòng họp AI',video:'Xưởng SEO & Veo 3',flow:'Google Flow · Tín dụng',shops:'Gian hàng & Profile',proxies:'Kho Proxy',products:'Kho sản phẩm',jobs:'Đơn đăng sản phẩm',memory:'Bộ nhớ tự học',telegram:'Telegram Bot',settings:'Cài đặt Gemini / Groq / AI',dom:'Học đăng bài'};
async function api(endpoint, body=null){
 const ctrl=new AbortController(), timer=setTimeout(()=>ctrl.abort(),endpoint==='overview'?6000:endpoint.endsWith('/veo-template/sample')?130000:endpoint.endsWith('/test-saved-agent')?55000:endpoint.endsWith('/test-chat')?30000:endpoint.endsWith('/test')?20000:12000);
 const opts=body===null?{signal:ctrl.signal}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:ctrl.signal};
 try{
  const response=await fetch('/api/'+endpoint,opts);
  const result=await response.json();
  if(!response.ok)throw Error(result.error||'Lỗi kết nối máy chủ');
  return result;
 }catch(err){
  if(err.name==='AbortError')throw Error('Máy chủ phản hồi chậm. Hãy kiểm tra /api/health và mức sử dụng CPU.');
  throw err;
 }finally{clearTimeout(timer)}
}
let refreshBusy=false,lastRefreshError='';
async function refresh(){
 if(refreshBusy)return;
 refreshBusy=true;
 try{data=await api('overview');lastRefreshError='';render()}
 catch(err){if(lastRefreshError!==err.message)toast('Không thể cập nhật: '+err.message,true);lastRefreshError=err.message}
 finally{refreshBusy=false}
}
function toast(message,isErr=false){const el=document.createElement('div');el.className='toast'+(isErr?' error':'');el.textContent=message;$('#toasts').append(el);setTimeout(()=>el.remove(),4300)}
function openModal(content){$('#modalBody').innerHTML=content;$('#modalBackdrop').hidden=false}
function closeModal(){$('#modalBackdrop').hidden=true;$('#modalBody').innerHTML=''}
const eButton=(text,fn='')=>`<button class="primary-btn" ${fn}>${text}</button>`;
const tag=(s)=>`<span class="chip ${s==='tiktok'?'purple':s==='shopee'?'orange':s==='done'?'':'gray'}">${h(s)}</span>`;
const fmtDate=s=>{if(!s)return '—';try{return new Date(s).toLocaleString('vi-VN',{hour:'2-digit',minute:'2-digit',day:'2-digit',month:'2-digit'})}catch{return s}};
const empty=(icon,title,desc)=>`<div class="empty"><span class="large">${icon}</span><b>${title}</b><div>${desc}</div></div>`;
function setMobileMenu(open){
 const expanded=Boolean(open&&window.matchMedia('(max-width: 920px)').matches);
 document.body.classList.toggle('menu-open',expanded);
 const toggle=$('#mobileMenuButton'),backdrop=$('#sidebarBackdrop');
 if(toggle){
  toggle.setAttribute('aria-expanded',String(expanded));
  toggle.setAttribute('aria-label',expanded?'Đóng menu điều hướng':'Mở menu điều hướng');
 }
 if(backdrop)backdrop.hidden=!expanded;
}
function navigate(view){
 if(activeView===view){setMobileMenu(false);return;}
 if(activeView==='settings'&&integrationDirty&&!confirm('Cấu hình AI có thay đổi chưa lưu. Rời trang và bỏ các thay đổi?'))return;
 integrationDirty=false;activeView=view;focusAgent=null;setMobileMenu(false);render();
 document.querySelector('#mainContent').scrollTo({top:0});if(view==='forum')loadForum()
 }
function pageHead(eyebrow,title,desc,right=''){return `<div class="page-head"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p>${desc}</p></div><div class="view-actions">${right}</div></div>`}
function svgText(str,x,y,size=12,color='#f2fff6',weight=700){return `<text x="${x}" y="${y}" fill="${color}" font-size="${size}" font-family="Arial, sans-serif" font-weight="${weight}" text-anchor="middle">${h(str)}</text>`}
function svgRoom(a,x,y){
  let col=a.color||'#76c0ff';
  const label=a.room||a.name,caption=a.name;
  return `<g class="room ${focusAgent===a.id?'agent-focus':''}" data-agent="${a.id}" transform="translate(${x},${y})" role="button" tabindex="0" aria-label="${h(label)}">
    <ellipse class="focus-ring" cx="0" cy="9" rx="91" ry="36" fill="#ffcb88" fill-opacity=".10" stroke="${col}" stroke-width="2" opacity=".2" />
    <polygon points="-66,-7 0,-45 74,-8 8,27" fill="#172d3d" opacity=".26" />
    <polygon points="-67,-55 -5,-93 70,-56 7,-19" fill="#e9f8e9" stroke="#fff8cb" stroke-width="2"/>
    <polygon points="-67,-55 7,-19 7,22 -67,-16" fill="#b6d4c9" stroke="#fff0bb" stroke-width="1"/>
    <polygon points="7,-19 70,-56 70,-15 7,22" fill="#90b8b9" stroke="#ffe6b5" stroke-width="1"/>
    <polygon points="-54,-54 -5,-81 50,-54 3,-26" fill="${col}" fill-opacity=".64" stroke="#ffffff" stroke-opacity=".55" stroke-width="1.2"/>
    <polygon points="-25,-69 -5,-81 50,-54 28,-41" fill="white" fill-opacity=".32" />
    <polygon points="-38,-16 -11,-1 -11,11 -38,-4" fill="#7faca8"/>
    <polygon points="21,-1 49,-17 49,-4 21,11" fill="#649b9c"/>
    <ellipse cx="1" cy="-47" rx="20" ry="8" fill="#51616c" opacity=".35" />
    <g class="head-badge"><circle cx="-1" cy="-62" r="15" fill="#183949" stroke="#e8fff8" stroke-width="2.5"/><circle cx="-7" cy="-63" r="3" fill="#b5f8e3"/><circle cx="5" cy="-63" r="3" fill="#b5f8e3"/><path d="M-7 -55 Q-1 -50 5 -55" fill="none" stroke="#b2ffde" stroke-width="2" stroke-linecap="round"/><circle cx="-1" cy="-82" r="3" fill="${col}"/></g>
    <g transform="translate(0,-135)"><rect x="-71" y="-12" width="142" height="39" rx="8" fill="#0b2634" stroke="${col}" stroke-width="1.7"/><rect x="-71" y="-12" width="5" height="39" rx="2" fill="${col}"/>${svgText(label,0,5,13)}${svgText(caption,0,19,9,'#8fc1c7',500)}</g>
  </g>`
}
function drawMap(){
 const rooms=[['research',238,314],['strategy',456,267],['creative',752,282],['ceo',537,438],['analyst',242,492],['compliance',814,470]];
 const rings=[...Array(31)].map((_,i)=>{const x=80+(i*137)%940,y=45+(i*89)%530;return `<circle cx="${x}" cy="${y}" r="${i%4===0?2:1}" fill="#c1e8f7" opacity=".${i%4+3}"/>`}).join('');
 const rocks=[[150,290,19],[346,195,13],[620,203,12],[940,345,18],[365,532,13],[868,530,10],[106,410,12],[590,535,8]].map(([x,y,r])=>`<g><ellipse cx="${x+6}" cy="${y+9}" rx="${r*1.5}" ry="${r*.6}" fill="#a94a37" opacity=".35"/><polygon points="${x-r},${y+4} ${x-7},${y-r} ${x+r*.7},${y-8} ${x+r},${y+5} ${x},${y+r*.65}" fill="#cb6750" stroke="#dc875e"/><polygon points="${x-7},${y-r} ${x+r*.7},${y-8} ${x+1},${y+1}" fill="#e99063"/></g>`).join('');
 return `<svg class="mars-svg" id="marsSvg" viewBox="0 0 1100 660" role="img" aria-label="Bản đồ trụ sở Sao Hỏa, chọn phòng để xem nhân viên AI">
 <defs>
  <radialGradient id="space" cx="50%" cy="45%"><stop stop-color="#19314a"/><stop offset="1" stop-color="#071329"/></radialGradient>
  <linearGradient id="soil" x1="0" y1="0" x2="1" y2=".8"><stop stop-color="#ffcf9e"/><stop offset=".56" stop-color="#f2a16b"/><stop offset="1" stop-color="#ce724e"/></linearGradient>
  <pattern id="gridpattern" width="42" height="42" patternUnits="userSpaceOnUse"><path d="M42 0H0V42" stroke="#3c6a8d" stroke-width=".8" fill="none" opacity=".24"/></pattern>
  <filter id="shadow"><feGaussianBlur stdDeviation="12"/></filter>
 </defs>
 <rect width="1100" height="660" fill="url(#space)"/><rect width="1100" height="660" fill="url(#gridpattern)"/>${rings}
 <circle cx="1050" cy="78" r="97" fill="#3988a9" opacity=".17"/><circle cx="1041" cy="79" r="65" fill="#478daa"/><path d="M1001 55q40-34 78-12t6 47q-35 5-52 30q-22-9-32-37z" fill="#4fbe9c" opacity=".8"/><ellipse cx="1017" cy="42" rx="40" ry="10" transform="rotate(-32 1017 42)" fill="#a0eff4" opacity=".16"/>
 <polygon points="118,170 795,127 1045,295 1000,575 298,612 68,413" transform="translate(0,16)" fill="#4e3338" filter="url(#shadow)" opacity=".5"/>
 <polygon points="118,170 795,127 1045,295 1000,575 298,612 68,413" fill="url(#soil)" stroke="#ffcc8f" stroke-width="2"/>
 <polygon points="68,413 298,612 1000,575 1000,595 298,636 68,433" fill="#995240"/>
 <polygon points="1000,575 1045,295 1045,311 1000,595" fill="#793d3d"/>
 <path d="M189 376L913 335M470 554L533 216M269 263L852 520M150 465L824 180" fill="none" stroke="#ffe1aa" stroke-width="15" stroke-linecap="round" opacity=".57"/>
 <path d="M189 376L913 335M470 554L533 216M269 263L852 520" fill="none" stroke="#fff5c9" stroke-width="3" stroke-dasharray="10 13" opacity=".55"/>
 <g opacity=".22" fill="none" stroke="#c65f47" stroke-width="9"><ellipse cx="365" cy="236" rx="32" ry="11" transform="rotate(-20 365 236)"/><ellipse cx="899" cy="399" rx="32" ry="12"/><ellipse cx="611" cy="548" rx="28" ry="11"/></g>
 ${rocks}
 <g transform="translate(715,153)"><ellipse rx="45" ry="13" fill="#ce694c" opacity=".4"/><path d="M-23 0V-88Q0-111 23-88V0z" fill="#f5efdf" stroke="#e1b483" stroke-width="3"/><path d="M-23-76Q0-121 23-76z" fill="#ff9f63"/><path d="M-19-7H19V1H-19z" fill="#59d9ce"/><path d="M-23-30L-42-10 0-18 40-10 23-30" fill="#ffcf8c"/><path d="M-15-65H15V-47H-15z" fill="#60c6d3"/></g>
 ${rooms.map(([id,x,y])=>svgRoom(data.agents.find(a=>a.id===id)||{id,name:id,room:id,color:'#65dccf'},x,y)).join('')}
 <g transform="translate(946,248)" data-view="shops" class="room"><rect x="-49" y="-15" width="98" height="33" rx="9" fill="#203e4e" stroke="#81ddbe" stroke-width="2"/>${svgText('SHOP CENTER',0,6,12)}<circle cx="0" cy="-38" r="18" fill="#40c7b7"/><path d="M-10 -41h21l-2 13h-16zM-7-49h16l3 8h-22z" fill="#eefaf3"/></g>
 <g transform="translate(650,553)" data-view="telegram" class="room"><rect x="-43" y="-13" width="86" height="28" rx="7" fill="#203e4e" stroke="#76c7ed" stroke-width="2"/>${svgText('TELEGRAM',0,5,11)}<circle cy="-39" r="18" fill="#2397d2"/><path d="M-9-41L11-50 6-28 0-35 -3-31 -4-39Z" fill="white"/></g>
 <g transform="translate(406,558)" data-view="memory" class="room"><rect x="-43" y="-13" width="86" height="28" rx="7" fill="#203e4e" stroke="#e2c68d" stroke-width="2"/>${svgText('TRÍ NHỚ',0,5,11)}<path d="M-22 -55Q0 -71 22-55V-30Q0-14-22-30Z" fill="#e7c782"/><path d="M-15 -52Q0 -63 15-52V-34Q0 -23-15-34Z" fill="#4b7282"/></g>
 </svg>`;
}
const miniTaskRow=(t,i)=>`<div class="mini-task"><span class="number-dot">${i+1}</span><div class="txt"><b>${h(t.title)}</b><small>${t.agent_id==='ceo'?'👑 AI CEO':'Lịch sử cũ: '+h(t.agent_id)} • ${fmtDate(t.created_at)}</small></div><span class="tag ${t.status==='done'?'done':''}">${h(t.status)}</span></div>`;
function home(){const s=data.stats,ms=data.missions.slice(0,4);return `
 ${pageHead('◈ MARS OPERATIONS','Trụ sở <span class="gradient-text">TEA AI Company</span>','Tập trung tạo tiêu đề SEO, mô tả SEO, phân tích giá, kịch bản 40 giây và 5 prompt Veo 3 cho từng sản phẩm.',eButton('👑 Giao việc cho CEO','onclick="showMissionForm()"'))}
 <div class="video-flow"><span>🏷 Tiêu đề & Mô tả SEO</span><b>→</b><span>💰 Giá bán lẻ</span><b>→</b><span>🎞 Kịch bản 40s</span><b>→</b><span>🎬 5 prompt Veo 3</span>
 <button class="small-btn" onclick="navigate('video')">Mở xưởng nội dung</button></div>
 <div class="metrics">
  ${[['♟','Nhân viên AI',s.agents||6,'CEO điều phối'],['🏷','Bộ nội dung',(data.commerce_outputs||[]).length,'Sản phẩm đã giao'],['🎬','Bộ Veo 3 đủ 5',(data.commerce_outputs||[]).filter(v=>v.veo_prompts).length,'Cảnh 8 giây'],['◫','Nhiệm vụ CEO',(data.missions||[]).length,'Tất cả nhiệm vụ']].map(x=>`<div class="metric"><span class="metric-icon">${x[0]}</span><div class="metric-label">${x[1]}</div><div class="metric-value">${x[2]}</div><div class="metric-caption">${x[3]}</div></div>`).join('')}
 </div>
 <div class="hq-grid"><section class="panel"><div class="panel-head"><div><h3>✦ Toàn cảnh trụ sở Sao Hỏa</h3><div class="sublabel">Nhấn vào tòa nhà để xem phòng ban; mọi lệnh đều gửi qua CEO</div></div><div class="map-tabs"><button class="${sceneMode==='mars'?'active':''}" onclick="sceneMode='mars';render()">Sao Hỏa</button><button class="${sceneMode==='plan'?'active':''}" onclick="sceneMode='plan';render()">Sơ đồ</button></div></div>
 <div class="map-container" id="sceneWrap">${sceneMode==='mars'?drawMap():organigram()}</div><div class="map-footer"><div class="legend"><span>Điều hành / dữ liệu</span><span>Sáng tạo</span><span>Nghiên cứu</span></div><div class="zoom"><button onclick="zoom(-0.1)">−</button><button onclick="sceneScale=1;zoom(0)">⌖</button><button onclick="zoom(0.1)">+</button></div></div></section>
 <div class="right-stack"><section class="panel mission-card"><div class="mission-card-top"><b>◫ Nhiệm vụ gần đây</b><span class="status-pill">${ms.length} nhiệm vụ</span></div>${ms.length?ms.map(miniTaskRow).join(''):empty('🪐','Trụ sở đang sẵn sàng','Giao nhiệm vụ đầu tiên cho AI CEO')}
 <button class="small-btn" style="width:100%;margin-top:15px" onclick="navigate('missions')">Xem tất cả nhiệm vụ →</button></section>
 <section class="panel padded"><h3>♟ Đội nhân viên AI</h3>${data.agents.slice(0,4).map(a=>`<div class="agent-line"><span class="agent-pic" style="background:${a.color}20">${a.emoji}</span><span class="desc"><strong>${a.name}</strong><small>${a.role}</small></span><span class="state">● Sẵn sàng</span></div>`).join('')}<button class="small-btn" style="width:100%;margin-top:15px" onclick="navigate('agents')">Xem cả 6 agent →</button></section></div></div>
 <div class="bottom-tiles"><button class="mini-tile" onclick="navigate('shops')"><span><strong>Quản lý gian hàng</strong><small>Profile Chrome và proxy riêng</small></span><span class="tile-icon">🏬</span></button><button class="mini-tile" onclick="navigate('telegram')"><span><strong>Nhận ảnh từ Telegram</strong><small>Đưa ảnh vào hàng đợi đăng bán</small></span><span class="tile-icon">📨</span></button><button class="mini-tile" onclick="navigate('memory')"><span><strong>Bộ nhớ AI tự học</strong><small>Ghi lại quy trình và kinh nghiệm</small></span><span class="tile-icon">🧠</span></button></div>`}
function organigram(){return `<div style="padding:23px;display:flex;align-items:center;justify-content:center;height:100%;flex-direction:column;gap:23px;background:radial-gradient(ellipse at center,#1a4050,#09182e)"><div style="border:1px solid #54c5b5;padding:14px 34px;border-radius:13px;background:#164050">👑 <b>AI CEO</b></div><div style="height:20px;width:1px;background:#5fd6c4"></div><div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:15px;width:100%">${data.agents.filter(a=>a.id!=='ceo').map(a=>`<button class="small-btn" style="padding:17px;border-color:${a.color};text-align:center" onclick="openAgent('${a.id}')">${a.emoji}<br><b>${a.name}</b><br><small>${a.role}</small></button>`).join('')}</div></div>`}
function zoom(by){sceneScale=Math.max(.65,Math.min(1.6,sceneScale+by));if($('#marsSvg'))$('#marsSvg').style.transform=`scale(${sceneScale})`}
function agentsView(){return `${pageHead('♟ TEAM MANAGEMENT','Nhân viên <span class="gradient-text">AI</span>','Phòng ban chỉ nhận việc qua AI CEO; bạn không giao việc trực tiếp.',eButton('👑 Giao việc cho CEO','onclick="showMissionForm()"'))}<div class="agents-cards">${data.agents.map(a=>`<div class="agent-card" onclick="openAgent('${a.id}')"><div class="portrait" style="background:${a.color}22;border:1px solid ${a.color}66">${a.emoji}</div><h3>${a.name}</h3><p>${a.role}</p><div class="bottom"><span>● Cấu hình sẵn</span><span>Xem nhiệm vụ ↗</span></div></div>`).join('')}</div><div class="note" style="margin-top:20px">Các agent là những vai trò logic trong phần mềm. Để xử lý AI thực sự, bạn phải cài Ollama và cấu hình workflow trong mã nguồn Python; trạng thái này không có nghĩa AI đang chạy nền.</div>`}
let flowCurrentEnrollment=null;
function flowView(){
 const accounts=data.flow_accounts||[],jobs=data.flow_jobs||[];
 const profiles=data.flow_browser_profiles||{};
 const reload=data.flow_reload_status||{};
 const canQueue=(data.commerce_outputs||[]).filter(x=>x.status==='ready'&&x.veo_prompts);
 const statusMap={queued:'Chưa có tài khoản đủ điểm',assigned:'Đã phân tài khoản – chờ thao tác Flow',completed:'Người dùng xác nhận đã tạo',cancelled:'Đã hủy'};
 const activeCount=accounts.filter(a=>a.enabled).length;
 const totalCredit=accounts.reduce((s,a)=>s+(Number.isFinite(a.balance)?a.balance:0),0);
 const proxies=data.proxies||[];
 const proxyOptions=proxies.map(p=>`<option value="${h(p.id)}">${h(p.name||p.id)} · ${h(p.host||'')} : ${h(p.port||'')}</option>`).join('');
 const rows=accounts.map((a,i)=>{
  const balance=a.balance===null?'—':Number(a.balance).toLocaleString('vi-VN');
  const state=!a.enabled?'TẠM TẮT':!a.fresh?'CẦN CẬP NHẬT':'ĐÃ BẬT';
  const stateClass=!a.enabled?'off':!a.fresh?'stale':'on';
  const masked=flowMaskEmail(a.email);
  const profile=profiles[a.email]||null;
  const profileState=profile?.status==='signin_pending'?'Đang chờ đăng nhập':profile?.status==='signin_verifying'?'Đang xác minh Gmail/điểm':profile?.status==='signin_wrong_account'?'Đăng nhập nhầm Gmail':profile?.status==='signin_captured'?'Đã nhận điểm, đang đóng':profile?.status==='signin_timeout'?'Chưa xác minh được':profile?.status==='signin_unmonitored'?'Không theo dõi được':profile?.status==='checking_credits'?'Đang đọc tín dụng':profile?.status==='credits_unavailable'?'Đọc điểm chưa thành công':profile?.status==='credits_updated'?'Đã lấy điểm từ Flow':profile?.in_use?'Đang mở Chrome':profile?.status==='error'?'Lỗi mở Chrome':profile?'Đã tạo profile':'Chưa tạo profile';
  return `<tr data-email="${h(a.email)}">
    <td class="flow-index">${i+1}</td>
    <td><button class="flow-switch ${a.enabled?'is-on':''}" type="button" role="switch" aria-checked="${Boolean(a.enabled)}" aria-label="${a.enabled?'Tạm tắt':'Bật lại'} ${h(a.email)}" onclick="flowToggleAccount(this,${!a.enabled})"><span></span></button></td>
    <td><input aria-label="Tạo ảnh (chưa hỗ trợ thiết lập riêng)" title="Chưa có thiết lập quyền tạo ảnh riêng theo tài khoản" type="checkbox" disabled></td>
    <td><input aria-label="Tạo video (chưa hỗ trợ thiết lập riêng)" title="Chưa có thiết lập quyền tạo video riêng theo tài khoản" type="checkbox" disabled></td>
    <td class="flow-email" title="${h(a.email)}">${h(masked)}<small class="flow-profile-sub" title="${h(profile?.message||'')}">${h(profileState)}${profile?' · '+h(profile.profile_id.slice(0,8)):''}</small></td>
    <td class="flow-plan" title="Chưa đồng bộ loại gói với Google Flow">—</td>
    <td class="flow-credit" title="${h(a.balance_source==='browser_dom'?'Tín dụng đọc từ giao diện Flow':'Tín dụng nhập thủ công')} · Đã dành ${Number(a.reserved)||0} điểm"><strong>${h(balance)}</strong><small>${a.balance_source==='browser_dom'?'Đọc từ Flow':'Nhập thủ công'} · Đã dành: ${Number(a.reserved)||0}</small></td>
    <td class="flow-proxy">—</td>
    <td><span class="flow-state ${stateClass}">${state}</span></td>
    <td class="flow-row-actions">
      <button class="flow-mini green" type="button" aria-label="Đọc tín dụng Google Flow của ${h(a.email)}" title="Đọc điểm từ Flow. Đóng Chrome profile này trước khi kiểm tra." onclick="flowCheckCredits(this)">↻</button>
      <button class="flow-mini neutral" type="button" aria-label="Nhập điểm thủ công của ${h(a.email)}" title="Nhập điểm thủ công / sửa tên profile" onclick="flowEditCredit(this)">✎</button>
      <button class="flow-mini orange" type="button" title="Mở Kho Proxy (chưa gán trực tiếp vào Gmail Flow)" onclick="navigate('proxies')">Proxy</button>
      <button class="flow-mini blue" type="button" onclick="flowOpenProfile(this)" aria-label="Mở Flow bằng profile của ${h(a.email)}" title="Mở Chrome profile riêng cho Gmail này">◎</button>
      <button class="flow-mini red" type="button" title="Xóa vĩnh viễn Gmail và dữ liệu Chrome profile sau khi đóng trình duyệt" aria-label="Xóa Gmail và profile Chrome" onclick="flowDeleteProfile(this)">▤</button>
      <details class="flow-row-editor"><summary>Chỉnh tín dụng / nhãn Chrome</summary>
       <div class="flow-row-editor-form"><input class="flow-credit-input" type="number" min="0" max="1000000" step="1" placeholder="Tín dụng đã kiểm tra" aria-label="Tín dụng Flow" value="${a.balance===null?'':a.balance}">
       <input class="flow-profile-input" type="text" maxlength="100" placeholder="Nhãn Chrome profile" aria-label="Nhãn profile" value="${h(a.profile_label||'')}">
       <button type="button" class="flow-btn blue" onclick="flowSaveCredit(this)">Lưu điểm</button></div>
       <small>Chỉ nhập số điểm bạn đã kiểm tra tại Flow. Không tự đồng bộ với Google.</small>
      </details>
    </td></tr>`;
 }).join('');
 const jobsHtml=jobs.map(j=>{
  const scene=Number(j.scene),id=Number(j.id);
  return `<article class="flow-job"><div class="video-work-top"><div>
   <strong>Video ${id} · Nhiệm vụ #${h(j.mission_id)} · Cảnh ${scene}/5</strong>
   <div class="tagline">${h(j.model)} · ${h(j.credit_cost)} điểm dự kiến/video</div></div>
   <span class="video-stage">${h(statusMap[j.status]||j.status)}</span></div>
   <div class="tagline">Tài khoản được phân: <b>${h(j.email||'Chưa có')}</b></div>
   <details><summary>Xem prompt cảnh ${scene}</summary><pre class="flow-prompt">${h(j.prompt)}</pre></details>
   <div class="video-card-actions">
    <button type="button" class="small-btn" onclick="flowCopyPrompt(${id})">Sao chép prompt</button>
    ${j.email?`<button type="button" class="small-btn" onclick="flowOpenJobProfile(${id})">Mở Flow đúng profile</button>`:`<button type="button" class="small-btn" disabled>Chưa phân Gmail</button>`}
    ${j.status==='assigned'?`<button type="button" class="small-btn" onclick="flowJobAction(${id},'complete')">Xác nhận video đã tạo</button>`:''}
    ${j.status!=='completed'&&j.status!=='cancelled'?`<button type="button" class="small-btn" onclick="flowJobAction(${id},'retry')">Phân lại</button>`:''}
   </div></article>`;
 }).join('');
 return `<div class="flow-ui">
 <section class="flow-surface">
  <header class="flow-section-header">↧ &nbsp; Thêm tài khoản mới</header>
  <div class="flow-pad">
   <p class="flow-green-note">Nhấn + Thêm tài khoản để mở Google Chrome thông thường. Đăng nhập Google Flow, sau đó đóng cửa sổ Chrome để phần mềm thử đọc Gmail và tín dụng. Không sử dụng Chrome tự động hóa trong bước đăng nhập.</p>
   ${flowCurrentEnrollment?`<div class="flow-enrollment-status" role="status"><strong>Chrome profile mới: ${h(flowCurrentEnrollment.status||'opening')}</strong><span>${h(flowCurrentEnrollment.message||'Đang mở Chrome...')}</span>${flowCurrentEnrollment.email?`<span>Gmail: ${h(flowCurrentEnrollment.email)} · Tín dụng: ${h(String(flowCurrentEnrollment.credits??'—'))}</span>`:''}
     ${flowCurrentEnrollment.status==='needs_manual'?`<div class="flow-enrollment-fallback"><p>Chrome đã lưu phiên, nhưng không đọc được thông tin tự động. Chỉ trong trường hợp này, nhập Gmail và điểm bạn nhìn thấy trong Google Flow để gắn vào profile đã đăng nhập.</p><input id="flowEnrollEmail" type="email" placeholder="Gmail đã đăng nhập" autocomplete="off"><input id="flowEnrollCredits" type="number" placeholder="Tín dụng Flow" min="0" step="1"><button class="flow-btn blue" type="button" onclick="flowConfirmEnrollment()">Lưu profile đã đăng nhập</button></div>`:''}
     </div>`:''}
   <div class="flow-proxy-bar">
    <label for="flowProxySelect">Proxy cho tài khoản (tùy chọn):</label>
    <select id="flowProxySelect" ${proxies.length?'':'disabled'}><option value="">Chọn proxy có sẵn</option>${proxyOptions}</select>
    <input type="text" disabled value="Chỉ kiểm tra proxy, chưa gán với Gmail Flow" aria-label="Ghi chú proxy">
    <button class="flow-btn blue" type="button" ${proxies.length?'':'disabled'} onclick="flowTestExistingProxy()">Kiểm tra Proxy</button>
   </div>
   <div class="flow-add-cards">
    <div class="flow-add-card">
      <b>Đăng nhập trình duyệt</b>
      <p class="flow-green-note small">Nhấn + Thêm tài khoản để mở Chrome thật. Bạn đăng nhập và đóng Chrome; sau đó phần mềm thử đọc email, tín dụng từ phiên đã lưu. Không cần nhập Gmail trước.</p>
      <div class="flow-card-buttons">
       <button class="flow-btn blue" type="button" onclick="flowEnrollAccount()">＋ Thêm tài khoản</button>
       <button class="flow-btn purple" type="button" onclick="flowShowAddForm(true)">＋ Thêm theo danh sách</button>
       <button class="flow-btn outline" type="button" onclick="flowBackupAccounts()">Sao lưu</button>
       <button class="flow-btn outline" type="button" onclick="flowRefreshAll()">Nạp lại</button>
      </div>
    </div>
    <div class="flow-add-card">
      <b>Nhập Cookie thủ công</b>
      <p>Không nhập cookie, mật khẩu hay OTP vào phần mềm. Hiện chưa hỗ trợ xác thực bằng cookie.</p>
      <input type="text" disabled placeholder="Dán chuỗi cookie vào đây..." aria-label="Nhập cookie chưa được hỗ trợ">
      <button class="flow-btn orange wide" type="button" disabled title="Không có backend xác thực cookie">＋ Thêm bằng Cookie (chưa hỗ trợ)</button>
    </div>
   </div>
   <div class="flow-add-inline" id="flowAddForm" hidden>
    <label for="flowEmailList" id="flowAddLabel">Gmail muốn thêm</label>
    <textarea id="flowEmailList" rows="2" placeholder="flow01@gmail.com&#10;flow02@gmail.com"></textarea>
    <div class="flow-form-actions"><button class="flow-btn blue" type="button" onclick="flowAddAccounts()">Tạo profile & mở Flow</button><button class="flow-btn outline" type="button" onclick="flowHideAddForm()">Đóng</button></div>
   </div>
  </div>
 </section>
 <section class="flow-surface">
  <header class="flow-section-header flow-header-between"><span>⚙ &nbsp; Tài khoản Flow</span><strong>Đang bật: ${activeCount} tài khoản | Tổng tín dụng: ${totalCredit.toLocaleString('vi-VN')}</strong></header>
  <div class="flow-pad">
   <div class="flow-toolbar">
    <strong>Bật tất cả:</strong>
    <button class="flow-btn green" type="button" onclick="flowToggleAll(true)">Bật</button>
    <button class="flow-btn outline" type="button" onclick="flowToggleAll(false)">Tắt</button>
    <label title="Chưa hỗ trợ thiết lập quyền tạo ảnh riêng"><input type="checkbox" disabled> Ảnh</label>
    <label title="Chưa hỗ trợ thiết lập quyền tạo video riêng"><input type="checkbox" disabled> Video</label>
    <label class="flow-unsupported" title="Chưa có tính năng tự tắt theo hạn mức Flow"><input type="checkbox" role="switch" disabled> Tự động tắt tài khoản bị hết giới hạn</label>
    <span class="flow-toolbar-space"></span>
    <span class="flow-ready-note">${reload.running?('Đang Reload: '+(reload.done||0)+'/'+(reload.total||0)+' profile · '+(reload.updated||0)+' cập nhật'):accounts.length?'Bấm Reload để lần lượt kiểm tra tín dụng từng Gmail.':'Chưa có tài khoản. Hãy thêm Gmail phía trên.'}</span>
    <button class="flow-btn green" type="button" onclick="flowRefreshAll()">Làm mới tất cả</button>
   </div>
   <div class="flow-table-scroll" role="region" aria-label="Danh sách tài khoản Google Flow" tabindex="0">
    <table class="flow-accounts-table">
     <thead><tr><th scope="col">#</th><th scope="col">TẮT/BẬT</th><th scope="col">Ảnh</th><th scope="col">Video</th><th scope="col">Tài khoản</th><th scope="col">Loại</th><th scope="col">Tín dụng</th><th scope="col">Proxy</th><th scope="col">Trạng thái</th><th scope="col">Hành động</th></tr></thead>
     <tbody>${rows||'<tr><td colspan="10" class="flow-empty">Chưa có Gmail. Chọn “Thêm tài khoản” ở khung phía trên.</td></tr>'}</tbody>
    </table>
   </div>
   <p class="flow-disclaimer">Nút Reload/Nạp lại sẽ lần lượt mở các profile đang bật ở chế độ đọc và cập nhật điểm tín dụng; không bật hàng loạt cửa sổ giao diện Chrome. Profile đang mở sẽ được bỏ qua để tránh xung đột. Nút ▤ xóa Gmail kèm thư mục Chrome sau khi xác nhận; thao tác không thể hoàn tác. Cookie vẫn chỉ lưu bên trong Chrome profile.</p>
  </div>
 </section>
 <details class="flow-queue-details">
  <summary>🎞 &nbsp; Hàng đợi 5 prompt Veo 3 <span>${jobs.length} cảnh · Nhấn để mở</span></summary>
  <div class="flow-pad">
   <div class="video-form-grid"><div class="field"><label for="flowMissionSelect">Bộ prompt đã hoàn thành và kiểm duyệt</label>
    <select id="flowMissionSelect">${canQueue.map(x=>`<option value="${x.mission_id}">${h('#'+x.mission_id+' · '+x.product_name)}</option>`).join('')}</select></div>
    <div class="field"><label for="flowModelSelect">Chế độ Flow / điểm dự kiến mỗi video</label>
    <select id="flowModelSelect"><option value="veo3.1-lite">Veo 3.1 Lite – 10 điểm*</option><option value="veo3.1-fast">Veo 3.1 Fast – 20 điểm*</option><option value="veo3.1-quality">Veo 3.1 Quality – 100 điểm*</option></select></div></div>
   <div class="video-card-actions"><button type="button" class="flow-btn blue" onclick="flowQueueMission()">Tạo hàng đợi 5 cảnh</button><button type="button" class="flow-btn outline" onclick="flowAllocate()">Phân bổ lại</button></div>
   <p class="flow-disclaimer">*Chi phí chỉ là ước tính. Kiểm tra chi phí và số dư thực tế trên Google Flow trước khi tạo video.</p>
   <div class="flow-job-list">${jobsHtml||empty('🎞','Chưa có hàng đợi','Tạo 5 prompt đã kiểm duyệt từ Xưởng SEO & Video AI.')}</div>
  </div>
 </details>
 </div>`;
}
function flowMaskEmail(email){
 const parts=String(email||'').split('@');
 if(parts.length!==2)return String(email||'');
 const s=parts[0];return s.length<=3?s[0]+'****@'+parts[1]:s.slice(0,4)+'****@'+parts[1];
}
async function flowEnrollAccount(){
 try{
  const r=await api('flow/enrollments/start',{});
  flowCurrentEnrollment={status:'opening',message:r.message};
  toast('Đang mở Chrome profile mới để bạn đăng nhập Google Flow');
  await refresh();
  flowWatchEnrollment(r.enrollment_id);
 }catch(e){toast('Không tạo được Chrome profile mới: '+e.message,true)}
}
async function flowWatchEnrollment(id){
 try{
  for(let i=0;i<360;i++){
   await new Promise(resolve=>setTimeout(resolve,2500));
   const state=await api('flow/enrollments/status?id='+encodeURIComponent(id));
   flowCurrentEnrollment=state;
   if(activeView==='flow')await refresh();
   if(state.status==='completed'){
    toast('Đã nhận tài khoản '+state.email+' · '+state.credits+' tín dụng. Chrome đã đóng.');
    return;
   }
   if(state.status==='needs_manual'){
    toast(state.message||'Cần xác nhận Gmail và tín dụng để lưu profile',true);
    return;
   }
   if(['duplicate','cancelled','failed'].includes(state.status)){
    toast(state.message||'Chưa thêm được tài khoản',true);
    return;
   }
  }
  toast('Phiên đăng nhập chưa hoàn tất; hãy kiểm tra Chrome đang mở.',true);
 }catch(e){toast('Không đọc được trạng thái Chrome: '+e.message,true)}
}
async function flowConfirmEnrollment(){
 const id=flowCurrentEnrollment?.id;
 const email=$('#flowEnrollEmail')?.value?.trim();
 const value=$('#flowEnrollCredits')?.value?.trim();
 if(!id||!email||value===undefined||value===''||!Number.isInteger(Number(value))||Number(value)<0){
  toast('Hãy nhập Gmail và số tín dụng nguyên không âm đang thấy trên Flow',true);return;
 }
 try{
  const result=await api('flow/enrollments/confirm',{id,email,credits:Number(value)});
  flowCurrentEnrollment=result;
  toast('Đã gắn tài khoản '+result.email+' vào Chrome profile đã đăng nhập.');
  await refresh();
 }catch(e){toast(e.message,true)}
}
function flowShowAddForm(bulk){
 const area=$('#flowAddForm'),field=$('#flowEmailList'),label=$('#flowAddLabel');
 if(!area||!field)return;
 area.hidden=false;field.rows=bulk?4:2;
 field.placeholder=bulk?'flow01@gmail.com\nflow02@gmail.com':'flow01@gmail.com';
 label.textContent=bulk?'Dán danh sách Gmail (mỗi dòng một địa chỉ)':'Thêm một địa chỉ Gmail';
 field.scrollIntoView({block:'nearest',behavior:'smooth'});field.focus();
}
function flowHideAddForm(){const x=$('#flowAddForm');if(x)x.hidden=true}
function flowFocusAdd(){flowShowAddForm(true)}
function flowEditCredit(button){
 const details=button.closest('tr')?.querySelector('.flow-row-editor');
 if(details){details.open=true;details.querySelector('input')?.focus()}
}
async function flowToggleAll(enabled){
 const accounts=(data.flow_accounts||[]).filter(a=>Boolean(a.enabled)!==enabled);
 if(!accounts.length){toast('Không có tài khoản nào cần đổi trạng thái');return}
 if(!confirm((enabled?'Bật':'Tắt')+' '+accounts.length+' tài khoản Flow trong danh sách?'))return;
 try{for(const a of accounts)await api('flow/accounts/enabled',{email:a.email,enabled});toast('Đã cập nhật '+accounts.length+' tài khoản');await refresh()}
 catch(e){toast('Một số tài khoản có thể chưa cập nhật: '+e.message,true);await refresh()}
}
function flowBackupAccounts(){
 const accounts=(data.flow_accounts||[]).map(a=>({email:a.email,profile_label:a.profile_label||'',balance:a.balance,balance_checked_at:a.balance_checked_at,enabled:Boolean(a.enabled)}));
 const blob=new Blob([JSON.stringify({exported_at:new Date().toISOString(),note:'Sao lưu danh sách và tín dụng nhập thủ công; không chứa mật khẩu/cookie.',accounts},null,2)],{type:'application/json;charset=utf-8'});
 const url=URL.createObjectURL(blob),link=document.createElement('a');
 link.href=url;link.download='flow-accounts-backup.json';document.body.appendChild(link);link.click();link.remove();URL.revokeObjectURL(url);
 toast('Đã tải bản sao lưu JSON danh sách Gmail. Không chứa mật khẩu hoặc cookie.');
}
async function flowTestExistingProxy(){
 const id=$('#flowProxySelect')?.value;if(!id){toast('Hãy chọn một proxy đã lưu trong Kho Proxy',true);return}
 try{const r=await api('proxies/test',{id});toast(r.message,!r.reachable)}
 catch(e){toast(e.message,true)}
}
let flowReloadPolling=false;
async function flowRefreshAll(){
 try{
  const r=await api('flow/profiles/reload-all',{});
  toast(r.message|| (r.started?'Đang kiểm tra tín dụng Google Flow':'Không có profile cần kiểm tra'));
  await refresh();
  if(r.running&&!flowReloadPolling)flowWatchReload();
 }catch(e){toast(e.message,true)}
}
async function flowWatchReload(){
 if(flowReloadPolling)return;
 flowReloadPolling=true;
 try{
  // Reload worker runs sequentially in backend. This loop only updates UI.
  for(let i=0;i<240;i++){
   await new Promise(resolve=>setTimeout(resolve,2500));
   const status=await api('flow/profiles/reload-status');
   if(activeView==='flow')await refresh();
   if(!status.running){
    toast(status.message||'Đã hoàn tất làm mới tín dụng',Boolean(status.failed||status.skipped));
    break;
   }
  }
 }catch(e){toast('Không lấy được tiến độ Reload: '+e.message,true)}
 finally{flowReloadPolling=false}
}
async function flowDeleteProfile(button){
 const email=button.closest('[data-email]')?.dataset.email;
 if(!email)return;
 const record=(data.flow_browser_profiles||{})[email];
 if(record?.in_use){
  toast('Hãy đóng cửa sổ Chrome của Gmail này trước khi xóa',true);return;
 }
 if(!confirm('XÓA VĨNH VIỄN Gmail '+email+' và toàn bộ dữ liệu Chrome profile?\nCookie/phiên đăng nhập trên profile này sẽ mất. Các video đang chờ sẽ được phân lại. Không thể hoàn tác.'))return;
 button.disabled=true;
 try{
  const result=await api('flow/profiles/delete',{email,confirm_delete:true});
  toast(result.warning||result.message,Boolean(result.warning));
  await refresh();
 }catch(e){toast(e.message,true);button.disabled=false}
}
async function flowAddAccounts(){
 const mails=$('#flowEmailList')?.value||'';
 try{
  const result=await api('flow/accounts/add',{emails:mails});
  toast(result.message);await refresh();
  // Opening is user initiated by clicking Add/Save; bulk creation must not open 100 windows.
  if(result.emails?.length===1)await flowStartLogin(result.emails[0]);
  else toast('Đã tạo '+(result.profiles_ready||0)+' profile. Chọn nút ◎ của mỗi Gmail để đăng nhập.');
 }catch(e){toast(e.message,true)}
}
async function flowCheckCredits(button){
 const email=button.closest('[data-email]')?.dataset.email;
 if(!email){toast('Không tìm thấy Gmail cần kiểm tra',true);return}
 try{
  button.disabled=true;
  const r=await api('flow/profiles/check-credits',{email});
  toast(r.message);
  await refresh();
  flowWatchCredits(email);
 }catch(e){toast(e.message,true)}
 finally{if(button.isConnected)button.disabled=false}
}
async function flowWatchCredits(email){
 for(let i=0;i<24;i++){
  await new Promise(resolve=>setTimeout(resolve,2500));
  await refresh();
  if(activeView!=='flow')return;
  const profile=data.flow_browser_profiles?.[email];
  if(profile?.status==='credits_updated'){
   const account=(data.flow_accounts||[]).find(a=>a.email===email);
   toast('Đã đọc tín dụng từ Flow: '+(account?.balance??'?')+' điểm');return;
  }
  if(profile?.status==='credits_unavailable'){
   toast(profile.message||'Không đọc được tín dụng. Vui lòng kiểm tra đăng nhập.',true);return;
  }
 }
 toast('Đang chờ Flow phản hồi. Bạn có thể nhấn Làm mới tất cả để xem kết quả.',true);
}
async function flowStartLogin(email){
 try{
  const result=await api('flow/profiles/login',{email});
  toast(result.message||'Đã yêu cầu mở Chrome để đăng nhập Google Flow');
  await refresh();
  flowWatchLogin(email);
 }catch(e){toast('Không mở được Chrome để đăng nhập: '+e.message,true)}
}
let flowLoginWatchers=new Set();
async function flowWatchLogin(email){
 if(flowLoginWatchers.has(email))return;
 flowLoginWatchers.add(email);
 try{
  for(let i=0;i<240;i++){
   await new Promise(resolve=>setTimeout(resolve,2500));
   if(activeView!=='flow')return;
   await refresh();
   const profile=data.flow_browser_profiles?.[email];
   if(profile?.status==='credits_updated'){
    const a=(data.flow_accounts||[]).find(x=>x.email===email);
    toast('Đăng nhập và cập nhật tín dụng hoàn tất: '+(a?.balance??'?')+' điểm. Chrome đã đóng.');
    return;
   }
   if(['signin_unmonitored','signin_timeout','closed','error'].includes(profile?.status)){
    toast(profile?.message||'Chưa xác minh được Gmail. Mở profile ◎ để đăng nhập thủ công.',true);
    return;
   }
  }
 }catch(e){toast('Không tải được trạng thái đăng nhập: '+e.message,true)}
 finally{flowLoginWatchers.delete(email)}
}
async function flowOpenProfileEmail(email){
 if(!email){toast('Chưa chọn Gmail Flow',true);return}
 try{
  const r=await api('flow/profiles/open',{email});
  toast(r.message);
  await refresh();
 }catch(e){toast(e.message,true)}
}
async function flowOpenProfile(button){
 const email=button.closest('[data-email]')?.dataset.email;
 await flowOpenProfileEmail(email);
}
async function flowOpenJobProfile(id){
 try{
  const r=await api('flow/jobs/open-profile',{job_id:id});
  toast('Cảnh #'+id+' dùng Gmail '+r.email+'. '+r.message);
  await refresh();
 }catch(e){toast(e.message,true)}
}
async function flowSaveCredit(button){
 const row=button.closest('[data-email]');
 if(!row)return;
 const raw=row.querySelector('.flow-credit-input')?.value;
 const label=row.querySelector('.flow-profile-input')?.value||'';
 if(raw===''||raw===undefined||!Number.isInteger(Number(raw))||Number(raw)<0){
  toast('Hãy nhập số điểm Flow nguyên không âm sau khi kiểm tra trên Google Flow',true);return
 }
 try{
  const r=await api('flow/accounts/balance',{email:row.dataset.email,balance:Number(raw),profile_label:label});
  toast(r.message);await refresh()
 }catch(e){toast(e.message,true)}
}
async function flowToggleAccount(button,enabled){
 const row=button.closest('[data-email]');if(!row)return;
 try{await api('flow/accounts/enabled',{email:row.dataset.email,enabled});await refresh()}
 catch(e){toast(e.message,true)}
}
async function flowQueueMission(){
 const mission=Number($('#flowMissionSelect')?.value);
 const model=$('#flowModelSelect')?.value;
 if(!Number.isInteger(mission)||mission<=0){toast('Chưa có bộ 5 prompt đã được kiểm duyệt',true);return}
 if(!confirm('Đưa 5 prompt vào hàng đợi phân tài khoản Flow? Thao tác này KHÔNG tự tạo video và không tiêu thụ điểm.'))return;
 try{
  const r=await api('flow/jobs/queue',{mission_id:mission,model});toast(r.message);await refresh()
 }catch(e){toast(e.message,true)}
}
async function flowAllocate(){
 try{
  const r=await api('flow/jobs/allocate',{});
  toast('Đã phân bổ '+r.assigned.length+' cảnh sang các Gmail đủ tín dụng đã khai báo');
  await refresh()
 }catch(e){toast(e.message,true)}
}
function flowCopyPrompt(id){
 const item=(data.flow_jobs||[]).find(x=>x.id===id);
 if(item)copyText(item.prompt);
}
async function flowJobAction(id,action){
 const item=(data.flow_jobs||[]).find(x=>x.id===id);
 if(!item)return;
 if(action==='complete'&&!confirm(
   'Bạn đã thực sự tạo xong video trên Google Flow bằng '+item.email+
   '? Phần mềm sẽ ghi trạng thái hoàn thành và trừ '+item.credit_cost+
   ' điểm ƯỚC TÍNH khỏi số dư đã nhập.'))return;
 try{
  const r=await api('flow/jobs/action',{
   job_id:id,action,confirm_flow_success:action==='complete',completed_url:''
  });
  toast(action==='complete'?'Đã ghi nhận video theo xác nhận của bạn':'Đã đưa prompt về hàng chờ và phân bổ lại');
  await refresh()
 }catch(e){toast(e.message,true)}
}
function videoRoomView(){
 const results=data.video_productions||[];
 const stages={research_pending:'Chờ nghiên cứu TikTok',research_complete:'Đã nghiên cứu',script_complete:'Đã soạn kịch bản',
 needs_review:'Chờ kiểm duyệt/chỉnh sửa',awaiting_video_render:'Đã có 5 prompt Veo 3',blocked:'Tạm dừng do lỗi'};
 return `${pageHead('▧ VIDEO WORKFLOW','Phòng <span class="gradient-text">SEO & Video AI</span>',
  'Bộ nội dung theo sản phẩm: SEO, giá bán lẻ, kịch bản 40 giây và 5 prompt Veo 3. Sau khi duyệt, phân bổ từng cảnh trong mục Google Flow.',
  eButton('👑 Tạo bộ nội dung sản phẩm','onclick="showMissionForm()"'))}
 <div class="video-flow"><span>🔎 Giá & thị trường</span><b>→</b><span>🏷 SEO</span><b>→</b><span>🎞️ Kịch bản 40s</span><b>→</b><span>🛡️ Duyệt</span><b>→</b><span>🎬 5 × 8s Veo 3</span></div>

 <section class="panel padded veo-base-panel">
 <div class="video-work-top"><div><h3>🧩 Prompt gốc Google Veo 3</h3>
 <p class="tagline">Dán prompt gốc bạn cung cấp. Các nhiệm vụ sản phẩm tạo sau dùng mẫu này để biến tấu nhiều kịch bản.</p></div>
 <span class="video-stage">${data.veo_template?.trim()?'Đã lưu mẫu':'Chưa có mẫu'}</span></div>
 <details><summary>${data.veo_template?.trim()?'Xem / chỉnh prompt mẫu':'Dán prompt Veo 3 mẫu của tôi'}</summary>
 <div class="field"><label for="veoTemplateTextarea">Mẫu Veo 3 · tối đa 16.000 ký tự</label>
 <textarea id="veoTemplateTextarea" rows="8" maxlength="16000" placeholder="Dán prompt; có thể dùng {product_name}, {ingredients}">${h(data.veo_template||'')}</textarea></div>
 <div class="video-card-actions"><button type="button" class="primary-btn" onclick="saveVeoTemplate()">💾 Lưu prompt mẫu</button></div>
 <div class="veo-sample-controls"><h4>🎬 Thử tạo kịch bản từ prompt mẫu</h4>
 <p class="tagline">Dùng prompt đang viết trong ô bên trên (kể cả chưa lưu), nhập sản phẩm để tạo bản nháp 40 giây. Chỉ AI CEO nhận yêu cầu này.</p>
 <div class="video-form-grid">
  <div class="field"><label for="veoSampleProduct">Tên sản phẩm</label><input type="text" id="veoSampleProduct" maxlength="180" placeholder="Ví dụ: Trà túi lọc đinh lăng"></div>
  <div class="field"><label for="veoSampleIngredients">Thành phần</label><textarea id="veoSampleIngredients" maxlength="2500" rows="2" placeholder="Nhập đúng thành phần ghi trên nhãn sản phẩm"></textarea></div>
 </div>
 <div class="video-card-actions"><button type="button" id="createVeoSampleButton" class="primary-btn" onclick="generateVeoSampleScript()">✨ Tạo kịch bản mẫu</button>
 <span class="hint" id="veoSampleStatus" role="status" aria-live="polite"></span></div>
 <div id="veoSamplePreview" class="veo-sample-preview" hidden></div>
 </div>
 <div class="note">Lưu database cục bộ. Bản thử chỉ hiển thị để xem và sao chép, không ghi đè prompt mẫu, không tự tạo MP4 hay đăng TikTok. Lệnh AI có thể tiêu thụ token/quota.</div></details></section>

 ${results.length?results.map(v=>{
 const brief=(data.video_briefs||{})[v.mission_id]||{};
 const badges=(brief.assets||[]).map(a=>`<a href="/api/mission-asset?mission_id=${v.mission_id}&asset_id=${a.id}" target="_blank" rel="noopener noreferrer">${a.kind==='image3d'?'🖼️ Ảnh 3D':'📄 Hồ sơ công bố'}: ${h(a.filename)}</a>`).join(' · ');
 return `<article class="panel padded video-work-card">
 <div class="video-work-top"><div><div class="eyebrow">NHIỆM VỤ #${v.mission_id}</div><h3>${h(v.product_name)}</h3></div><span class="video-stage">${h(stages[v.status]||v.status)}</span></div>
 <div class="tagline">Thành phần: ${h(brief.ingredients||'Chưa cung cấp')}</div>
 <div class="video-asset-links">${badges||'Không có tệp đính kèm'}</div>
 <div class="video-card-actions"><button class="small-btn" onclick="showVideoRoomDetail(${v.mission_id})">Xem 5 đầu ra SEO & Video</button>
 <button class="small-btn" onclick="showCEOReport(${v.mission_id})">Báo cáo CEO</button></div>
 </article>`;}).join(''):empty('🎬','Chưa có dự án video','Giao brief sản phẩm cho AI CEO để khởi chạy quy trình.')}
 <div class="note">Các URL TikTok chỉ được lưu làm tham chiếu. Nghiên cứu nội dung cần ghi chú hoặc transcript mà chủ cung cấp; hệ thống không tự truy cập video riêng tư. Giấy công bố chưa được xác nhận pháp lý chỉ là tư liệu tham khảo.</div>`;
}
function sampleScriptText(scenes){
 return scenes.map(x=>
  'CẢNH '+x.scene+' ('+((x.scene-1)*8)+'–'+(x.scene*8)+' giây)\n'+
  'Hình ảnh/hành động: '+x.action+'\nLời thoại: '+(x.dialogue||'Không lời thoại')+
  '\nPROMPT GOOGLE VEO 3:\n'+x.veo_prompt
 ).join('\n\n--------------------\n\n');
}
async function generateVeoSampleScript(){
 const name=$('#veoSampleProduct')?.value.trim()||'';
 const ingredients=$('#veoSampleIngredients')?.value.trim()||'';
 const template=$('#veoTemplateTextarea')?.value||'';
 const button=$('#createVeoSampleButton'),status=$('#veoSampleStatus');
 const preview=$('#veoSamplePreview');
 if(name.length<2||ingredients.length<2){
  toast('Cần nhập tên sản phẩm và thành phần để tạo kịch bản mẫu',true);
  return;
 }
 if(!confirm('Gửi yêu cầu tạo kịch bản mẫu 40 giây cho AI CEO? Phép thử gọi API mô hình và có thể sử dụng token/quota hoặc phát sinh phí theo cấu hình tài khoản.'))return;
 if(button){button.disabled=true;button.textContent='Đang tạo qua AI CEO...'}
 if(status)status.textContent='AI CEO đang soạn 5 cảnh × 8 giây. Không rời trang khi đang tạo bản thử.';
 if(preview){preview.hidden=true;preview.replaceChildren()}
 try{
  const result=await api('content/veo-template/sample',{
   product_name:name,ingredients,template,confirm_token_use:true
  });
  if(!Array.isArray(result.scenes)||result.scenes.length!==5)
   throw Error('Không nhận được đủ 5 cảnh từ AI CEO');
  const parts=result.scenes.map(x=>{
   return '<section class="video-scene-card">'+
    '<div class="video-work-top"><h4>Cảnh '+Number(x.scene)+'/5 · 8 giây</h4>'+
    '<button type="button" class="small-btn" data-copy-scene="'+Number(x.scene)+'">Sao chép prompt</button></div>'+
    '<div class="tagline"><strong>Hình ảnh:</strong> '+h(x.action)+'</div>'+
    '<div class="tagline"><strong>Thoại:</strong> '+h(x.dialogue||'Không thoại')+'</div>'+
    '<pre>'+h(x.veo_prompt)+'</pre></section>';
  }).join('');
  if(preview){
   preview.innerHTML='<div class="video-work-top"><h4>🎞️ Kịch bản mẫu · '+h(result.product_name)+' · 40 giây</h4>'+
    '<button type="button" class="small-btn" id="copyFullVeoSample">Sao chép toàn bộ kịch bản</button></div>'+
    '<div class="note">Đây là bản nháp để duyệt, chưa qua kiểm duyệt pháp lý và chưa render video.</div>'+
    parts;
   preview.hidden=false;
   preview.querySelector('#copyFullVeoSample').addEventListener('click',
     ()=>copyText(sampleScriptText(result.scenes)));
   preview.querySelectorAll('[data-copy-scene]').forEach(btn=>
     btn.addEventListener('click',()=>{
       const scene=Number(btn.dataset.copyScene);
       const selected=result.scenes.find(x=>x.scene===scene);
       if(selected)copyText(selected.veo_prompt);
     }));
  }
  if(status)status.textContent='✓ Đã tạo bản nháp 5 cảnh, mỗi cảnh 8 giây. Xem kết quả bên dưới.';
 }catch(err){
  if(status)status.textContent='✕ '+err.message;
  toast('Không tạo được kịch bản mẫu: '+err.message,true);
 }finally{
  if(button){button.disabled=false;button.textContent='✨ Tạo kịch bản mẫu'}
 }
}
async function saveVeoTemplate(){
 const input=$('#veoTemplateTextarea');if(!input)return;
 try{
  const result=await api('content/veo-template',{template:input.value});
  toast(result.message||'Đã lưu prompt mẫu Veo 3');await refresh();
 }catch(e){toast('Không lưu được mẫu: '+e.message,true)}
}
function commerceFor(id){
 return (data.commerce_outputs||[]).find(x=>x.mission_id===id)||{};
}
function commerceScenes(id){
 try{
  const raw=JSON.parse(commerceFor(id).veo_prompts||'');
  return Array.isArray(raw.scenes)?raw.scenes:[];
 }catch(_){return []}
}
function copyCommerce(id,key,scene=0){
 const c=commerceFor(id);let content=String(c[key]||'');
 if(key==='veo_prompts'&&scene){
  const row=commerceScenes(id).find(x=>x.scene===scene);
  content=row?.veo_prompt||'';
 }
 if(!content){toast('Nội dung chưa sẵn sàng',true);return}
 copyText(content);
}
function showVideoRoomDetail(id){
 const v=(data.video_productions||[]).find(x=>x.mission_id===id);
 if(!v)return;
 const brief=(data.video_briefs||{})[id]||{};
 const commerce=commerceFor(id), scenes=commerceScenes(id);
 const status=v.status==='awaiting_video_render'?'Sẵn sàng đưa vào công cụ tạo video sau khi chủ duyệt':
  v.status==='needs_review'?'Tạm dừng: cần kiểm duyệt/chỉnh sửa':'Đang trong quy trình';
 const part=(title,txt)=>`<details class="video-detail-section"><summary>${title}</summary><pre>${h(txt||'Chưa có kết quả')}</pre></details>`;
 const sceneMarkup=scenes.length===5
  ?scenes.map(x=>`<div class="video-scene-card">
   <div class="video-work-top"><h4>Cảnh ${x.scene}/5 · ${x.duration_seconds} giây</h4>
   <button class="small-btn" onclick="copyCommerce(${id},'veo_prompts',${x.scene})">Sao chép prompt cảnh ${x.scene}</button></div>
   <pre>${h(x.veo_prompt)}</pre><div class="tagline">Thoại: ${h(x.dialogue||'Không thoại')}</div>
   </div>`).join('')
  :`<pre>${h(commerce.veo_prompts||'Chưa có 5 prompt hợp lệ. Chờ kiểm duyệt và kết quả Phòng Video AI.')}</pre>`;
 openModal(`<div class="eyebrow">VIDEO AI • DỰ ÁN #${id}</div><h2>${h(v.product_name)}</h2>
 <div class="note">${h(status)}</div>
 ${part('🏷 Tiêu đề SEO Shopee / TikTok Shop',commerce.seo_title)}
 <button class="small-btn" onclick="copyCommerce(${id},'seo_title')">Sao chép tiêu đề SEO</button>
 ${part('📝 Mô tả sản phẩm SEO',commerce.seo_description)}
 <button class="small-btn" onclick="copyCommerce(${id},'seo_description')">Sao chép mô tả SEO</button>
 ${part('💰 Nghiên cứu giá bán lẻ · nguồn cần xác minh',commerce.retail_price)}
 <button class="small-btn" onclick="copyCommerce(${id},'retail_price')">Sao chép giá bán lẻ</button>
 ${part('🎬 Kịch bản video bán hàng 40 giây · 5 cảnh × 8 giây',commerce.script_40s)}
 <button class="small-btn" onclick="copyCommerce(${id},'script_40s')">Sao chép kịch bản 40 giây</button>
 <details class="video-detail-section" open><summary>🎥 5 prompt Google Veo 3 · mỗi cảnh 8 giây</summary>
 ${sceneMarkup}</details>
 <div class="video-card-actions"><button type="button" class="primary-btn" onclick="closeModal();navigate('flow')">🎬 Chuyển 5 prompt sang hàng đợi Google Flow</button></div>
 ${part('🔎 Nghiên cứu TikTok',v.research)}
 ${part('✍️ Kịch bản bán hàng',v.script)}
 ${part('🛡️ Kiểm duyệt',v.compliance)}
 ${part('🎬 Gói storyboard gửi Phòng Video AI',v.storyboard)}
 <div class="note">Không có MP4 render tự động. Cần kết nối công cụ video và chủ doanh nghiệp duyệt trước khi xuất bản.</div>
 <button class="small-btn" onclick="closeModal();showCEOReport(${id})">Xem báo cáo CEO</button>`);
}
function missionsView(){const ms=data.missions;return `${pageHead('👑 CEO COMMAND CENTER','Nhiệm vụ <span class="gradient-text">AI CEO</span>','Bạn chỉ giao việc cho CEO. CEO phân công nội bộ, cập nhật tiến độ và báo cáo trực tiếp cho bạn.',eButton('👑 Giao nhiệm vụ CEO','onclick="showMissionForm()"'))}<section class="panel"><div class="table-wrap">${ms.length?`<table class="data-table"><thead><tr><th>Mã</th><th>Nhiệm vụ</th><th>Đầu mối</th><th>Trạng thái</th><th>Ngày tạo</th><th>Báo cáo</th></tr></thead><tbody>${ms.map(m=>`<tr><td>#${m.id}</td><td><strong>${h(m.title)}</strong><div class="tagline">${h(m.detail).slice(0,90)}</div></td><td>👑 AI CEO</td><td>${tag(m.status)}${m.ceo_error?`<div class="tagline" style="max-width:230px;color:#ffad9b">${h(m.ceo_error).slice(0,150)}</div>`:''}</td><td>${fmtDate(m.created_at)}</td><td><div class="inline-actions"><button class="small-btn" onclick="showCEOReport(${m.id})">Xem tiến độ / báo cáo</button><button class="small-btn" onclick="openForum(${m.id})">◉ Xem log tranh luận</button>${m.status==='blocked'?`<button class="small-btn" onclick="retryCEOTask(${m.id})">↻ Thử lại</button>`:''}</div></td></tr>`).join('')}</tbody></table>`:empty('👑','Chưa có nhiệm vụ','Hãy giao nhiệm vụ đầu tiên cho AI CEO.')}</div></section><div class="panel padded" style="margin-top:16px"><h3>🧠 Bộ não AI theo vị trí – Ngôn ngữ tiếng Việt</h3>
<div class="note">Các agent đặt chế độ TỰ ĐỘNG sẽ ưu tiên Gemini, sau đó Groq. Claude/OpenAI chỉ được dự phòng khi bạn cho phép; Ollama là phương án cuối.</div>
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin:14px 0">
${['ceo','strategy','compliance','research','creative','analyst'].map(agent=>{const config=(data.model_routing?.routes||{})[agent]||{provider:'ollama'};
return `<div style="border:1px solid #315062;border-radius:10px;padding:12px">
<strong>${h(actorName(agent))}</strong><div class="tagline">${config.provider==='openai'?'OpenAI – '+h(config.model):config.provider==='claude'?'Claude – '+h(config.model):config.provider==='auto'?'Tự động – '+h(config.model):config.provider==='gemini'?'Gemini – '+h(config.model):config.provider==='groq'?'Groq – '+h(config.model):'Ollama – Máy cá nhân'}</div></div>`}).join('')}
</div><div class="note">Ưu tiên: ${h((data.model_routing?.priority||[]).join(' → '))}. Gemini: ${data.model_routing?.gemini_key_configured?'Đã lưu key':'Chưa lưu key'}; Groq: ${data.model_routing?.groq_key_configured?'Đã lưu key':'Chưa lưu key'}.
<br>Cho phép dự phòng trả phí: ${data.model_routing?.allow_paid_fallback?'Có':'Không'}.
<br>Chi phí Claude/OpenAI ghi nhận (ước tính): ${(Number(data.claude_usage?.estimated_usd||0)+Number(data.openai_usage?.estimated_usd||0)).toFixed(4)} USD tháng này.
<br>Ollama: ${data.ollama?.running?(data.ollama.model_ready?'Đã kết nối – '+h(data.ollama.model):'Đang chạy, chưa tải model '+h(data.ollama.model)):'Chưa kết nối'}.
<br>Thông tin này là cấu hình và trạng thái kết nối, không bảo đảm API luôn sẵn sàng; kết quả thử kết nối có trong trang Cài đặt AI.</div></div>`}

function kindText(kind){
 return ({assignment:'Giao việc',proposal:'Đề xuất',question:'Câu hỏi',objection:'Phản biện / trả lời',
           response:'Trả lời',revision:'Điều chỉnh phương án',decision:'CEO chốt phương án',
           error:'Lỗi xử lý',retry:'Chạy lại nhiệm vụ'})[kind]||kind;
}
function actorName(id){return ({ceo:'👑 AI CEO',research:'🔭 Research',strategy:'🎯 Strategy',
 creative:'🎨 Creative',analyst:'📊 Analyst',compliance:'🛡️ Compliance',
 system:'⚙️ Hệ thống'})[id]||id}
function forumRow(m){
 const end=m.kind==='decision';
 return `<div style="border:1px solid ${end?'#52a69c':'#315062'};border-radius:12px;padding:13px 15px;margin:10px 0;background:${end?'#122f34':'#122735'}">
 <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap">
 <strong>${h(actorName(m.sender))} → ${h(actorName(m.recipient))}</strong>
 <small style="color:#93bbd2">${h(kindText(m.kind))} · ${h(fmtDate(m.created_at))}</small></div>
 <div style="margin-top:8px;white-space:pre-wrap;line-height:1.6">${h(m.body)}</div></div>`;
}
function forumView(){
 const tasks=(data.missions||[]).filter(m=>m.agent_id==='ceo');
 if(!forumMissionId&&tasks.length)forumMissionId=tasks[0].id;
 const selected=tasks.find(m=>m.id===forumMissionId);
 const rows=forumData?.mission?.id===forumMissionId?forumData.messages:[];
 const title=selected?`Nhiệm vụ #${selected.id} – ${h(selected.title)}`:'Chưa có nhiệm vụ';
 return `${pageHead('◉ INTERNAL DEBATE ROOM','Phòng họp <span class="gradient-text">AI</span>',
 'Theo dõi câu hỏi, phản biện và góp ý nội bộ; chỉ AI CEO chốt phương án và báo cáo cho bạn.',
 eButton('👑 Giao nhiệm vụ cho CEO','onclick="showMissionForm()"'))}
 <div class="panel padded">
 <label style="display:block;margin-bottom:8px">Chọn cuộc họp theo nhiệm vụ CEO</label>
 <select style="max-width:100%;min-width:280px" onchange="selectForumMission(this.value)">
 ${tasks.map(m=>`<option value="${m.id}" ${m.id===forumMissionId?'selected':''}>#${m.id} – ${h(m.title)} (${h(m.status)})</option>`).join('')}
 </select>
 <div class="note" style="margin-top:15px">Đây là nhật ký trao đổi công việc được AI tạo ra, không phải suy luận nội bộ ẩn. Tối đa 2 agent tranh luận, số vòng được giới hạn để tránh treo máy. Không nhân viên nào gửi lệnh trực tiếp cho chủ doanh nghiệp.</div>
 </div>
 <div class="panel padded" style="margin-top:16px">
 <div class="panel-head"><h3 id="forumTitle">${title}</h3><button class="small-btn" onclick="loadForum()">↻ Làm mới log</button></div>
 <div id="forumFinal" class="note">${forumData?.mission?.id===forumMissionId&&forumData.final_decision?'👑 CEO đã chốt phương án. Xem bên dưới.':'Chưa có quyết định cuối của CEO.'}</div>
 <div id="forumEntries" style="margin-top:12px;max-height:64vh;overflow-y:auto" aria-live="polite">
 ${rows.length?rows.map(forumRow).join(''):empty('◉','Chưa có log trao đổi','Khi CEO nhận nhiệm vụ, các lượt giao việc, câu hỏi và phản biện sẽ xuất hiện tại đây.')}
 </div></div>`;
}
function selectForumMission(id){
 forumMissionId=Number(id);
 forumData=null;
 render();
 loadForum();
}
function openForum(id){
 forumMissionId=Number(id);
 forumData=null;
 closeModal();
 navigate('forum');
 loadForum();
}
async function loadForum(){
 if(forumBusy||!forumMissionId||activeView!=='forum')return;
 forumBusy=true;
 const id=forumMissionId;
 try{
  const result=await api('agent-forum?mission_id='+encodeURIComponent(id));
  if(activeView!=='forum'||id!==forumMissionId)return;
  forumData=result;
  const entries=$('#forumEntries'), final=$('#forumFinal'), title=$('#forumTitle');
  if(title)title.textContent='Nhiệm vụ #'+result.mission.id+' – '+result.mission.title+' ('+result.mission.status+')';
  if(final)final.textContent=result.final_decision?'👑 CEO đã chốt phương án. Xem tin nhắn cuối của CEO.':'Chưa có quyết định cuối của CEO.';
  if(entries)entries.innerHTML=result.messages.length?result.messages.map(forumRow).join(''):
    '<div class="empty-sm">Chưa có lượt trao đổi; nhiệm vụ có thể đang chờ hoặc Ollama chưa chạy.</div>';
 }catch(e){if(activeView==='forum'){const el=$('#forumEntries');if(el)el.textContent='Không tải được log: '+e.message;}}
 finally{forumBusy=false}
}
function sessionChip(a){
 const s=a.session||{},state=s.status||'unknown';
 const words={logged_in:'🟢 Đã xác minh đăng nhập',logged_out:'🔴 Đã đăng xuất',verification_required:'🟡 Cần xác minh OTP/CAPTCHA',unknown:'⚪ Chưa xác định',error:'⚠️ Lỗi kiểm tra',checking:'⏳ Đang kiểm tra'};
 const status=words[state]||words.unknown;
 const stamp=s.checked_at?'Kiểm tra: '+fmtDate(s.checked_at):'Chưa có lần kiểm tra';
 const details=s.message||'';
 return `<div><strong>${h(status)}</strong><div class="tagline">${h(stamp)} • kiểm tra bằng giao diện Seller Center</div><div class="tagline" style="max-width:230px">${h(details)}</div>${a.profile_open?'<small class="chip">Chrome đang mở</small>':''}</div>`;
}
function shopsView(){const shops=data.accounts;return `${pageHead('▣ MULTI-SHOP HUB','Gian hàng & <span class="gradient-text">Chrome Profile</span>','Mỗi gian hàng có Chrome Profile, proxy và trạng thái phiên đăng nhập riêng.',eButton('+ Thêm gian hàng','onclick="showShopForm()"'))}
 <div class="two-cols"><section class="panel"><div class="panel-head"><h3>Danh sách gian hàng</h3><small>${shops.length} tài khoản</small></div><div class="table-wrap">${shops.length?`<table class="data-table"><thead><tr><th>Tài khoản</th><th>Nền tảng</th><th>Proxy đang dùng</th><th>Đăng nhập</th><th>Thao tác</th></tr></thead><tbody>${shops.map(a=>`<tr><td><strong>${h(a.name)}</strong><div class="tagline">${h(a.id)}</div></td><td>${tag(a.platform)}</td><td>${a.proxy_id?tag(a.proxy_id):(a.proxy?tag('Cấu hình cũ'):tag('Không proxy'))}</td><td>${sessionChip(a)}</td><td><div class="inline-actions"><button class="small-btn" onclick="openProfile('${a.id}')">↗ Mở Chrome</button><button class="small-btn" onclick="checkShopSession('${a.id}')">✓ Kiểm tra đăng nhập</button><button class="small-btn" onclick="showAssignProxy('${a.id}')">⇄ Gán proxy</button><button class="small-btn" onclick="showTrainForm('${a.id}')">◉ Học đăng bài</button></div></td></tr>`).join('')}</tbody></table>`:empty('🏬','Chưa có gian hàng','Tạo gian hàng để mở profile và dạy thao tác mẫu.')}</div></section>
 <section class="panel padded"><h3>🧩 Thao tác hoàn toàn trên giao diện</h3>${[['01','Thêm proxy','Nhập host, port, username và mật khẩu ngay trong cửa sổ phần mềm.'],['02','Gán proxy','Chọn proxy từ danh sách để liên kết với profile cần dùng.'],['03','Mở Chrome','Đăng nhập thủ công trong cửa sổ của gian hàng; lần sau tái sử dụng profile.'],['04','Học thao tác','Nhấn nút Học đăng bài, thao tác mẫu rồi nhấn Dừng & lưu.']].map(r=>`<div class="info-row"><span class="ic">${r[0]}</span><div><strong>${r[1]}</strong><p>${r[2]}</p></div></div>`).join('')}<button class="small-btn" style="margin-top:15px" onclick="navigate('proxies')">Mở kho Proxy →</button></section></div>`}
function proxiesView(){const ps=data.proxies||[];return `${pageHead('⇄ PROXY MANAGER','Quản lý <span class="gradient-text">Proxy</span>','Nhập, chỉnh sửa, xóa và gán proxy bằng chuột ngay trên phần mềm.',eButton('+ Thêm proxy','onclick="showProxyForm()"'))}
 <section class="panel"><div class="panel-head"><h3>Danh sách proxy của bạn</h3><small>${ps.length} proxy</small></div><div class="table-wrap">${ps.length?`<table class="data-table"><thead><tr><th>Mã</th><th>Máy chủ</th><th>Loại</th><th>Đăng nhập</th><th>Profile sử dụng</th><th>Thao tác</th></tr></thead><tbody>${ps.map(p=>`<tr><td><strong>${h(p.name)}</strong><div class="tagline">${h(p.id)}</div></td><td><code>${h(p.host)}:${p.port}</code></td><td>${tag(p.scheme)}</td><td>${p.username?`<span class="chip">${h(p.username)} ••••</span>`:'<span class="chip gray">Không</span>'}</td><td>${h(data.accounts.filter(a=>a.proxy_id===p.id).map(a=>a.id).join(', ')||'Chưa gán')}</td><td><div class="inline-actions"><button class="small-btn" onclick="showProxyForm('${p.id}')">Sửa</button><button class="small-btn" onclick="testProxy('${p.id}')">Thử kết nối</button><button class="small-btn" onclick="deleteProxy('${p.id}')">Xóa</button></div></td></tr>`).join('')}</tbody></table>`:empty('⇄','Chưa có proxy','Bấm Thêm proxy để nhập địa chỉ, cổng và tài khoản proxy.')}</div></section>
 <div class="note" style="margin-top:16px">Mật khẩu proxy được lưu trong kho bí mật của hệ điều hành qua thư viện keyring (không đưa vào JSON, SQLite hay Telegram). Proxy chỉ kết nối mạng; nó không bảo đảm duy trì đăng nhập hoặc vượt xác minh của sàn.</div>`}
function productsView(){const rows=Object.entries(data.products);return `${pageHead('◉ PRODUCT LIBRARY','Kho <span class="gradient-text">trà túi lọc</span>','Hồ sơ chuẩn cho mỗi SKU: tên, mô tả, giá bán và tồn kho.',eButton('+ Thêm sản phẩm','onclick="showProductForm()"'))}<section class="panel"><div class="table-wrap"><table class="data-table"><thead><tr><th>Mã SKU</th><th>Tên sản phẩm</th><th>Giá (VND)</th><th>Tồn kho</th><th>Trạng thái</th></tr></thead><tbody>${rows.map(([sku,p])=>`<tr><td><strong>${h(sku)}</strong></td><td>${h(p.title)}</td><td>${p.price===null?'Chưa có':Number(p.price).toLocaleString('vi-VN')+'đ'}</td><td>${p.stock??'Chưa có'}</td><td>${p.price!==null&&p.stock!==null&&!p.title.includes('THAY BẰNG')?'<span class="chip">Có dữ liệu</span>':'<span class="chip orange">Cần hoàn thiện</span>'}</td></tr>`).join('')}</tbody></table></div></section>`}
function jobsView(){const rows=data.jobs;return `${pageHead('▤ PRODUCT LISTING','Nhiệm vụ <span class="gradient-text">đăng sản phẩm</span>','Mọi yêu cầu đăng sản phẩm được gửi vào hàng đợi AI CEO.',eButton('👑 Giao CEO đăng sản phẩm','onclick="showJobForm()"'))}<section class="panel"><div class="table-wrap">${rows.length?`<table class="data-table"><thead><tr><th>ID</th><th>SKU</th><th>Shop/Profile</th><th>Chế độ</th><th>Ảnh</th><th>Trạng thái</th><th>Thao tác</th></tr></thead><tbody>${rows.map(j=>`<tr><td>#${j.id}</td><td><strong>${h(j.sku)}</strong></td><td>${tag(j.shop)}<div class="tagline">${h(j.account_id)}</div></td><td>${h(j.mode)}</td><td>${j.images}</td><td>${tag(j.status)}</td><td>${j.status==='received'?`<button class="small-btn" onclick="approveJob(${j.id})">Duyệt</button><button class="small-btn" onclick="rejectJob(${j.id})">Bỏ</button>`:'<span class="tagline">Kiểm tra từ Telegram/CLI</span>'}</td></tr>`).join('')}</tbody></table>`:empty('📦','Chưa có nhiệm vụ đăng bán','Gửi yêu cầu đến AI CEO. Job chỉ được tạo sau bước phân công của CEO.')}</div></section><div class="note warning" style="margin-top:16px">Việc duyệt đòi hỏi đã có ảnh, giá và tồn kho thật. Phiên bản GUI chưa tự đăng sản phẩm lên hai sàn, thao tác cuối cần người quản lý thực hiện.</div>`}
function memoryView(){const ls=data.learnings;return `${pageHead('✧ LONG TERM MEMORY','Bộ nhớ <span class="gradient-text">AI tự học</span>','Lưu kinh nghiệm có nguồn và trạng thái kiểm chứng để các agent có thể sử dụng.',eButton('+ Thêm bài học','onclick="showLearningForm()"'))}<div class="two-cols"><section class="panel"><div class="panel-head"><h3>Thẻ kiến thức được lưu</h3><small>${ls.length} bài học</small></div>${ls.length?ls.map(l=>`<div style="padding:17px;border-bottom:1px solid #244253"><div>${tag(l.validation)} ${tag(l.category)}</div><h3 style="font-size:14px;margin:9px 0 4px">${h(l.title)}</h3><p class="tagline" style="margin:0">${h(l.description)}</p><small style="color:#658fa8">${h(l.source)||'Chưa đính kèm nguồn'} • ${fmtDate(l.created_at)}</small></div>`).join(''):empty('🧠','Bộ nhớ còn trống','Tạo bài học đầu tiên từ thực chiến hoặc tài liệu đã xác minh.')}</section><section class="panel padded"><h3>Vòng lặp học hỏi</h3>${[['1','Đọc nguồn đã cho phép'],['2','Đưa ra giả thuyết'],['3','Thử nghiệm thực tế'],['4','Đánh giá kết quả'],['5','Lưu bài học đã kiểm chứng']].map(([n,t])=>`<div class="info-row"><span class="number-dot">${n}</span><strong>${t}</strong></div>`).join('')}<div class="note warning" style="margin-top:15px">Bản GUI hiện lưu kiến thức thủ công; chưa có dịch vụ nghiên cứu tự động chạy nền. Mở rộng này cần kết nối workflow AI.</div></section></div>`}
const agentName={ceo:'AI CEO',strategy:'AI Strategy',compliance:'AI Compliance',
 research:'AI Research',creative:'AI Creative',analyst:'AI Analyst'};
function aiSettingsSection(){
 const cfg=data.connection_settings||{}, providers=cfg.agent_providers||{},
      claudeModels=cfg.claude_models||{},openaiModels=cfg.openai_models||{};
 const roles=['ceo','strategy','compliance','research','creative','analyst'];
 return `<section class="panel padded" style="min-width:0">
 <div class="integration-hero">
 <div class="integration-eyebrow">TRUNG TÂM CẤU HÌNH AI</div>
 <h2>Gemini chính <span>·</span> Groq dự phòng</h2>
 <p>Ba bước thiết lập rõ ràng. Không cần sửa .env, AI CEO vẫn là người chốt phương án.</p>
 <div class="integration-route"><span>01 <b>Gemini</b></span><span aria-hidden="true">→</span><span>02 <b>Groq</b></span><span aria-hidden="true">→</span><span>03 <b>Ollama</b></span></div>
 </div>
 <form id="aiSettingsForm" class="integration-form" onsubmit="saveAISettings(event)" oninput="markIntegrationDirty()" onchange="markIntegrationDirty()">
 <div class="integration-section-title"><span>BƯỚC 1</span><div><h3>Kết nối hai dịch vụ AI</h3><p>Nhập API key của bạn, bấm kiểm tra, sau đó lưu ở cuối trang.</p></div></div>
 <div class="integration-key-layout">
 <article class="integration-key-card">
 <div class="integration-key-top"><span class="integration-key-icon">✦</span><span><strong>Google Gemini</strong><small>Nhà cung cấp chính</small></span>
 <span class="integration-key-status ${cfg.gemini_key_configured?'is-saved':''}">${cfg.gemini_key_configured?'● Đã lưu':'○ Chưa lưu'}</span></div>
 <label class="integration-field-label" for="geminiApiKeyInput">Gemini API Key</label>
 <div class="integration-input-wrap"><input id="geminiApiKeyInput" name="gemini_api_key" type="password" autocomplete="new-password" spellcheck="false"
 placeholder="${cfg.gemini_key_configured?'Khóa đã lưu · để trống nếu không đổi':'Dán Gemini API key tại đây'}">
 <button type="button" class="integration-show-btn" onclick="toggleIntegrationKey('geminiApiKeyInput',this)" aria-label="Hiện hoặc ẩn Gemini API key">Hiện</button></div>
 <div class="integration-key-helper">${cfg.gemini_key_configured?'Đã lưu trong database SQLite mã hóa trên máy.':'Có thể kiểm tra trước khi lưu khóa.'}
 <a href="https://aistudio.google.com/api-keys" target="_blank" rel="noopener noreferrer">Lấy API key</a></div>
 <div class="integration-key-actions"><button type="button" class="small-btn" onclick="testConnection('gemini')">✓ Kiểm tra Gemini</button>
 ${cfg.gemini_key_configured?'<button type="button" class="integration-danger" onclick="removeIntegrationSecret(\'gemini\')">Xóa khóa</button>':''}</div>
 <div id="geminiConnectionResult" class="integration-feedback" role="status" aria-live="polite" hidden></div>
 </article>
 <article class="integration-key-card">
 <div class="integration-key-top"><span class="integration-key-icon">↗</span><span><strong>GroqCloud</strong><small>Dự phòng khi Gemini gián đoạn</small></span>
 <span class="integration-key-status ${cfg.groq_key_configured?'is-saved':''}">${cfg.groq_key_configured?'● Đã lưu':'○ Chưa lưu'}</span></div>
 <label class="integration-field-label" for="groqApiKeyInput">Groq API Key</label>
 <div class="integration-input-wrap"><input id="groqApiKeyInput" name="groq_api_key" type="password" autocomplete="new-password" spellcheck="false"
 placeholder="${cfg.groq_key_configured?'Khóa đã lưu · để trống nếu không đổi':'Dán Groq API key tại đây'}">
 <button type="button" class="integration-show-btn" onclick="toggleIntegrationKey('groqApiKeyInput',this)" aria-label="Hiện hoặc ẩn Groq API key">Hiện</button></div>
 <div class="integration-key-helper">${cfg.groq_key_configured?'Đã lưu trong database SQLite mã hóa trên máy.':'Có thể kiểm tra trước khi lưu khóa.'}
 <a href="https://console.groq.com/keys" target="_blank" rel="noopener noreferrer">Lấy API key</a></div>
 <div class="integration-key-actions"><button type="button" class="small-btn" onclick="testConnection('groq')">✓ Kiểm tra Groq</button>
 <button type="button" class="small-btn" onclick="testGroqChat()">Thử như mã Python mẫu (GPT-OSS-120B)</button>
 <button type="button" class="small-btn" onclick="testGroqSavedCEO()">★ Kiểm tra khóa đã lưu + model AI CEO</button>
 ${cfg.groq_key_configured?'<button type="button" class="integration-danger" onclick="removeIntegrationSecret(\'groq\')">Xóa khóa</button>':''}</div>
 <p class="integration-key-helper">Kiểm tra Groq và thử như Python mẫu có thể dùng khóa vừa dán (chưa lưu). Nút <strong>★ Kiểm tra khóa đã lưu + model AI CEO</strong> chỉ dùng khóa SQLite và model CEO đã lưu, giống đường xử lý nhiệm vụ. Hãy bấm Lưu cấu hình AI trước nếu vừa thay key. Các phép thử tạo văn bản dùng một ít token/quota.</p>
 <div id="groqConnectionResult" class="integration-feedback" role="status" aria-live="polite" hidden></div>
 </article></div> <div class="integration-section-title"><span>BƯỚC 2</span><div><h3>Chọn chế độ vận hành</h3><p>Ưu tiên miễn phí, không tự gọi Claude/OpenAI tính phí.</p></div></div>
 <section class="integration-settings-area">
 <label class="checkbox-line">
 <input type="checkbox" name="free_only" onchange="updateFreeOnlyControls()" ${cfg.free_only!==false?'checked':''}>
 <span><strong>Chỉ dùng model có gói API miễn phí</strong><small style="display:block;color:#9ebccc;margin-top:4px">Khóa API Claude/OpenAI trả phí, kể cả dự phòng.</small></span></label>
 <p class="tagline">Free Tier phụ thuộc hạn mức và gói billing thực tế của Google/Groq. Model có gói miễn phí vẫn có thể bị tính tiền nếu tài khoản đã bật thanh toán.</p>
 <div class="integration-key-actions">
 <button type="button" class="primary-btn" onclick="preferFreePreset()">✦ Áp dụng cấu hình đề xuất cho 6 agent</button></div>
 </section>
 <div class="integration-section-title"><span>BƯỚC 3</span><div><h3>Tùy chỉnh từng AI Agent</h3><p>Mặc định đã được lựa chọn. Chỉ cần mở phần này khi muốn chỉnh model.</p></div></div>
  <details class="integration-expander" id="agentModelSettings">
 <summary>Điều chỉnh model cho 6 agent <small>Mở rộng khi cần</small></summary>
 <p class="tagline">Chỉ AI CEO chốt phương án. Gemini và Groq là các model miễn phí theo hạn mức của nhà cung cấp.</p>
 <div class="integration-agent-grid">${roles.map(a=>{
 const provider=providers[a]||'auto';
 return `<article class="integration-agent-card">
 <h4>${agentName[a]} <span class="integration-agent-meta">· ${a==='ceo'?'Quyết định':a==='creative'||a==='analyst'?'Tác vụ nhẹ':'Chuyên môn'}</span></h4>
 <div class="field integration-agent-provider"><label>Nhà cung cấp</label><select name="provider_${a}" aria-label="Nhà cung cấp cho ${agentName[a]}">
 ${[['auto','Tự động: Gemini → Groq → Ollama'],['gemini','Gemini (có Free Tier)'],['groq','Groq (có Free Plan)'],['claude','Claude (trả phí)'],['openai','OpenAI (trả phí)'],['ollama','Ollama cục bộ']].map(p=>`<option value="${p[0]}" ${p[0]===provider?'selected':''} ${cfg.free_only!==false&&['claude','openai'].includes(p[0])?'disabled':''}>${p[1]}</option>`).join('')}
 </select></div>
 <div class="integration-agent-fields">
 <div class="field"><label>Gemini chính</label><select name="gemini_model_${a}" aria-label="Model Gemini cho ${agentName[a]}">${['gemini-3.8-flash','gemini-3.6-flash','gemini-3.5-flash-lite','gemini-3.1-flash-lite','gemini-2.5-flash','gemini-2.5-flash-lite'].map(m=>`<option value="${m}" ${m===(cfg.gemini_models?.[a]||(a==='creative'||a==='analyst'?'gemini-3.5-flash-lite':'gemini-3.8-flash'))?'selected':''}>${m}</option>`).join('')}</select></div>
 <div class="field"><label>Groq dự phòng</label><select name="groq_model_${a}" aria-label="Model Groq cho ${agentName[a]}">${['openai/gpt-oss-120b','openai/gpt-oss-20b','qwen/qwen3.8-27b'].map(m=>`<option value="${m}" ${m===(cfg.groq_models?.[a]||(a==='creative'||a==='analyst'?'openai/gpt-oss-20b':'openai/gpt-oss-120b'))?'selected':''}>${m}</option>`).join('')}</select></div></div>
 <details class="integration-expander"><summary>Model trả phí</summary>
 <div class="integration-agent-fields"><div class="field"><label>Claude</label><select name="claude_model_${a}" aria-label="Model Claude cho ${agentName[a]}">
 ${['claude-sonnet-4-6','claude-opus-4-6','claude-haiku-4-5'].map(m=>`<option value="${m}" ${m===(claudeModels[a]||'claude-sonnet-4-6')?'selected':''}>${m}</option>`).join('')}
 </select></div>
 <div class="field"><label>OpenAI</label><select name="openai_model_${a}" aria-label="Model OpenAI cho ${agentName[a]}">
 ${['gpt-6.1-sol','gpt-6-luna'].map(m=>`<option value="${m}" ${m===(openaiModels[a]||'gpt-6-luna')?'selected':''}>${m}</option>`).join('')}
 </select></div></div></details></article>`}).join('')}</div></details>
 <details class="integration-expander">
 <summary>⚙ API trả phí và tùy chọn nâng cao <small>Claude · OpenAI · Ngân sách</small></summary>
 <p class="tagline">Chỉ sử dụng khi bạn chủ động tắt chế độ miễn phí. Các khóa được mã hóa trong database SQLite cục bộ.</p>
 <label class="checkbox-line"><input type="checkbox" name="allow_paid_fallback" ${cfg.allow_paid_fallback?'checked':''} ${cfg.free_only!==false?'disabled':''}> Cho phép tự dự phòng sang Claude/OpenAI trả phí</label>
 <div class="integration-paid-grid"><div class="field"><label>Claude API Key (Anthropic)</label>
 <input id="claudeApiKeyInput" type="password" name="claude_api_key" autocomplete="new-password" placeholder="${cfg.claude_key_configured?'Đã lưu khóa Claude – để trống nếu không thay đổi':'Nhập Claude API key tại đây'}">
 <small>${cfg.claude_key_configured?'✓ Đã lưu API key trong database mã hóa':'Chưa cấu hình Claude API key'}</small>
 <button class="integration-show-btn" type="button" onclick="toggleIntegrationKey('claudeApiKeyInput',this)">Hiện</button></div>
 <div class="field"><label>Ngân sách Claude tháng (USD, chỉ là giới hạn ước tính cục bộ)</label>
 <input name="claude_monthly_limit_usd" type="number" min="0.5" max="1000" step="0.5" value="${Number(cfg.claude_monthly_limit_usd||12)}"></div>
 <div class="field"><label>OpenAI API key – chỉ dùng khi bạn chọn OpenAI</label>
 <input id="openaiApiKeyInput" type="password" name="openai_api_key" autocomplete="new-password" placeholder="${cfg.openai_key_configured?'Đã lưu khóa OpenAI – để trống nếu không đổi':'Không bắt buộc khi chỉ dùng Claude'}">
 <small>${cfg.openai_key_configured?'✓ Đã lưu API key trong database mã hóa':'Chưa lưu OpenAI key'}</small>
 <button class="integration-show-btn" type="button" onclick="toggleIntegrationKey('openaiApiKeyInput',this)">Hiện</button></div>
 <div class="field"><label>Ngân sách OpenAI tháng (USD)</label>
 <input name="monthly_limit_usd" type="number" min="0.5" max="1000" step="0.5" value="${Number(cfg.monthly_limit_usd||12)}"></div>
</div>
 <div class="integration-key-actions">
 <button type="button" class="small-btn" onclick="testConnection('claude')">Kiểm tra Claude</button>
 <button type="button" class="small-btn" onclick="testConnection('openai')">Kiểm tra OpenAI</button>
 <button type="button" class="integration-danger" onclick="removeIntegrationSecret('claude')" ${cfg.claude_key_configured?'':'disabled'}>Xóa khóa Claude</button>
 <button type="button" class="integration-danger" onclick="removeIntegrationSecret('openai')" ${cfg.openai_key_configured?'':'disabled'}>Xóa khóa OpenAI</button></div>
 <p class="tagline">Chi phí API ước tính tháng này: Claude ${Number(data.claude_usage?.estimated_usd||0).toFixed(4)} USD · OpenAI ${Number(data.openai_usage?.estimated_usd||0).toFixed(4)} USD.</p>
 <div class="integration-key-actions"><button type="button" class="small-btn" onclick="preferClaudePreset()">Dùng Claude cho các agent</button>
 <button type="button" class="small-btn" onclick="preferBalancedPreset()">Claude CEO/Strategy/Compliance</button></div>
 </details>
 <div class="integration-savebar">
 <div><strong id="aiUnsavedIndicator">Cấu hình đã tải</strong><small>Thay đổi chỉ có hiệu lực sau khi lưu.</small><span id="aiSaveFeedback" class="integration-save-feedback" role="status" aria-live="polite" hidden></span></div>
 <button id="saveAISettingsButton" type="submit" class="primary-btn">Lưu cấu hình AI</button>
 </div>
 </form> </section>`;
}
function storedKeyProvider(id){
 return ({geminiApiKeyInput:'gemini',groqApiKeyInput:'groq',
          claudeApiKeyInput:'claude',openaiApiKeyInput:'openai',
          telegramBotTokenInput:'telegram'})[id]||null;
}
function keyValueForSave(field){
 const input=$('#'+field);
 return input?.dataset?.savedReveal==='1'?'':(input?.value||'');
}
function hideStoredKey(input,button){
 input.type='password';
 if(input.dataset.savedReveal==='1'){
   input.value='';input.readOnly=false;
   delete input.dataset.savedReveal;
 }
 button.textContent='Hiện';
 button.setAttribute('aria-pressed','false');
}
async function toggleIntegrationKey(id,button){
 const input=document.getElementById(id);if(!input)return;
 if(input.type==='text'){
  hideStoredKey(input,button);return;
 }
 // Unsaved user-entered keys are revealed locally, without an API request.
 if(input.value&&input.dataset.savedReveal!=='1'){
  input.type='text';button.textContent='Ẩn';
  button.setAttribute('aria-pressed','true');return;
 }
 const provider=storedKeyProvider(id);
 if(!provider){toast('Trường khóa không hợp lệ',true);return;}
 if(!confirm('Hiện API key/token đã lưu trên màn hình? Hãy bảo đảm không có người khác đang xem màn hình của bạn.'))return;
 button.disabled=true;button.textContent='Đang đọc...';
 try{
  const response=await fetch('/api/settings/secret/reveal',{
    method:'POST',credentials:'same-origin',cache:'no-store',
    headers:{'Content-Type':'application/json','X-Requested-With':'Tea-Mars-UI'},
    body:JSON.stringify({provider,confirm_reveal:true})
  });
  const result=await response.json();
  if(!response.ok||!result.ok)throw Error(result.error||'Không thể đọc khóa đã lưu');
  input.value=result.secret;
  input.dataset.savedReveal='1';
  input.readOnly=true; // Hide first before editing or replacing a stored key.
  input.type='text';button.textContent='Ẩn';
  button.setAttribute('aria-pressed','true');
  // Reveal is transient. Never keep decrypted keys in visible input indefinitely.
  setTimeout(()=>{
   if(input.dataset.savedReveal==='1'&&input.type==='text')
    hideStoredKey(input,button);
  },60000);
 }catch(err){
  toast('Không xem được khóa: '+err.message,true);
  button.textContent='Hiện';
 }finally{button.disabled=false;}
}
function updateFreeOnlyControls(){
 const form=$('#aiSettingsForm');if(!form)return;
 const enabled=form.elements['free_only'].checked;
 const fallback=form.elements['allow_paid_fallback'];
 if(enabled){fallback.checked=false;fallback.disabled=true;}else{fallback.disabled=false;}
 for(const role of ['ceo','strategy','compliance','research','creative','analyst']){
  const field=form.elements['provider_'+role];
  for(const option of field.options){
   if(['claude','openai'].includes(option.value))option.disabled=enabled;
  }
  if(enabled&&['claude','openai'].includes(field.value))field.value='auto';
 }
}
function preferFreePreset(){
 const form=$('#aiSettingsForm');if(!form)return;
 for(const a of ['ceo','strategy','compliance','research','creative','analyst']){
   form.elements['provider_'+a].value='auto';
   const light=['creative','analyst'].includes(a);
   form.elements['gemini_model_'+a].value=light?'gemini-3.5-flash-lite':'gemini-3.8-flash';
   form.elements['groq_model_'+a].value=light?'openai/gpt-oss-20b':'openai/gpt-oss-120b';
 }
 form.elements['free_only'].checked=true;
 form.elements['allow_paid_fallback'].checked=false;
 updateFreeOnlyControls();
 markIntegrationDirty();
 toast('Đã chọn Gemini → Groq → Ollama, chặn Claude/OpenAI trả phí. Bấm Lưu để áp dụng.');
}
function preferClaudePreset(){
 const form=$('#aiSettingsForm');if(!form)return;
 if(form.elements['free_only'].checked){toast('Hãy tắt Chỉ sử dụng model có gói miễn phí trước khi chọn Claude.',true);return;}
 for(const a of ['ceo','strategy','compliance','research','creative','analyst']){
   form.elements['provider_'+a].value='claude';
   form.elements['claude_model_'+a].value=['creative','analyst'].includes(a)?'claude-haiku-4-5':'claude-sonnet-4-6';
 }
 markIntegrationDirty();
 toast('Đã chọn Claude cho các agent. Bấm Lưu cấu hình AI để áp dụng.');
}
function preferBalancedPreset(){
 const form=$('#aiSettingsForm');if(!form)return;
 if(form.elements['free_only'].checked){toast('Hãy tắt Chỉ sử dụng model có gói miễn phí trước khi chọn Claude.',true);return;}
 for(const a of ['ceo','strategy','compliance','research','creative','analyst']){
   const use=['ceo','strategy','compliance'].includes(a);
   form.elements['provider_'+a].value=use?'claude':'ollama';
   form.elements['claude_model_'+a].value='claude-sonnet-4-6';
 }
 markIntegrationDirty();
 toast('Đã chọn Claude cho CEO/Strategy/Compliance. Bấm Lưu để áp dụng.');
}
function telegramSettingsSection(){
 const cfg=data.connection_settings||{},bot=data.telegram_process||{};
 return `<section class="panel padded"><h3>➤ Cài đặt Telegram Bot</h3>
 <p class="tagline">Lưu token, ID người được phép và điều khiển Bot bằng nút trên giao diện.</p>
 <form id="telegramSettingsForm" onsubmit="saveTelegramSettings(event)">
 <div class="field"><label>Bot Token (tạo bằng @BotFather)</label>
 <input id="telegramBotTokenInput" type="password" name="bot_token" autocomplete="new-password"
 placeholder="${cfg.telegram_token_configured?'Đã lưu token – để trống để giữ nguyên':'Dán bot token ở đây'}">
 <small>${cfg.telegram_token_configured?'✓ Đã lưu token mã hóa trong database':'Chưa lưu Telegram Bot Token'}</small>
 <button type="button" class="integration-show-btn" onclick="toggleIntegrationKey('telegramBotTokenInput',this)">Hiện</button></div>
 <div class="field"><label>Telegram User ID được phép (phân cách bằng dấu phẩy)</label>
 <input name="telegram_allowed_ids" value="${h((cfg.telegram_allowed_ids||[]).join(','))}" placeholder="Ví dụ: 123456789 (để trống để lấy ID qua /myid)">
 <small>Chưa biết User ID? Lưu token trước, bấm Bật Bot, mở Telegram nhắn <b>/myid</b> cho bot để lấy ID. Sau đó Tắt Bot → nhập ID → Lưu → Bật lại. Khi chưa có ID, các lệnh khác đều bị chặn.</small></div>
 <label class="checkbox-line"><input type="checkbox" name="telegram_autostart" ${cfg.telegram_autostart?'checked':''}>
 Tự chạy Telegram Bot khi khởi động Mars Studio</label>
 <div class="form-bottom" style="display:flex;gap:8px;flex-wrap:wrap">
 <button class="primary-btn" type="submit" ${bot.running?'disabled':''}>Lưu Telegram</button>
 <button class="small-btn" type="button" onclick="testConnection('telegram')">✓ Kiểm tra token</button>
 <button class="small-btn" type="button" onclick="controlTelegram('start')" ${bot.running?'disabled':''}>▶ Bật Bot</button>
 <button class="small-btn" type="button" onclick="controlTelegram('stop')" ${bot.running?'':'disabled'}>■ Tắt Bot</button>
 <button class="small-btn" type="button" onclick="removeIntegrationSecret('telegram')" ${cfg.telegram_token_configured&&!bot.running?'':'disabled'}>Xóa token đã lưu</button></div>
 </form>
 <div class="note" style="margin-top:12px">${bot.running?'🟢 Telegram Bot đang chạy':'⚪ Telegram Bot chưa chạy'} • ${h(bot.message||'')}.
 Bot nhận ảnh và bản nháp theo chức năng hiện có, không tự đăng sản phẩm lên sàn.</div>
 <div class="tagline">Để tạo Bot: vào Telegram → tìm <strong>@BotFather</strong> → gửi /newbot. Bạn cần biết User ID dạng số của tài khoản được phép sử dụng.</div>
 </section>`;
}
let integrationDirty=false;
function markIntegrationDirty(){integrationDirty=true;const e=$('#aiUnsavedIndicator');if(e)e.textContent='● Có thay đổi chưa lưu';}
function settingsView(){
 return `${pageHead('⚙ AI PROVIDERS','Cài đặt <span class="gradient-text">Gemini / Groq / AI</span>',
 'Quản lý Gemini, Groq và mô hình cho các AI Agent · Không cần sửa file .env')}${aiSettingsSection()}`;
}
function telegramView(){return `${pageHead('➤ TELEGRAM CONNECTOR','Telegram <span class="gradient-text">Bot</span>',
 'Thiết lập và vận hành bot nhận ảnh ngay trong phần mềm.','')}
 <div class="two-cols">${telegramSettingsSection()}
 <section class="panel padded"><h3>Mẫu gửi ảnh sản phẩm</h3>
 <div class="note" style="white-space:pre-wrap">SKU=TRA-001
MODE=new
ACCOUNTS=shopee_01,tiktok_01</div>
 <button class="small-btn" style="margin-top:15px" onclick="copyText('SKU=TRA-001\\nMODE=new\\nACCOUNTS=shopee_01,tiktok_01')">Sao chép mẫu</button>
 <div class="note warning" style="margin-top:18px">Không gửi mật khẩu, OTP, cookie Shopee hoặc OpenAI API key qua Telegram. Cần được cấp quyền Bot trước khi dùng.</div></section></div>`;}
async function saveAISettings(event){
 event.preventDefault();
 const e=new FormData(event.target),roles=['ceo','strategy','compliance','research','creative','analyst'];
 const payload={
  gemini_api_key:keyValueForSave('geminiApiKeyInput'),groq_api_key:keyValueForSave('groqApiKeyInput'),
  claude_api_key:keyValueForSave('claudeApiKeyInput'),openai_api_key:keyValueForSave('openaiApiKeyInput'),
  free_only:e.get('free_only')==='on',
  allow_paid_fallback:e.get('allow_paid_fallback')==='on',
  provider_priority:['gemini','groq','claude','openai','ollama'],
  claude_monthly_limit_usd:Number(e.get('claude_monthly_limit_usd')),
  monthly_limit_usd:Number(e.get('monthly_limit_usd')),
  agent_providers:Object.fromEntries(roles.map(a=>[a,e.get('provider_'+a)])),
  gemini_models:Object.fromEntries(roles.map(a=>[a,e.get('gemini_model_'+a)])),
  groq_models:Object.fromEntries(roles.map(a=>[a,e.get('groq_model_'+a)])),
  claude_models:Object.fromEntries(roles.map(a=>[a,e.get('claude_model_'+a)])),
  openai_models:Object.fromEntries(roles.map(a=>[a,e.get('openai_model_'+a)]))
 };
 const button=$('#saveAISettingsButton'),feedback=$('#aiSaveFeedback');
 if(button){button.disabled=true;button.textContent='Đang lưu...';}
 if(feedback){feedback.hidden=false;feedback.textContent='Đang lưu cấu hình an toàn trên máy...';}
 try{
  const r=await api('settings/ai',payload);
  integrationDirty=false;
  if(feedback)feedback.textContent='✓ Đã lưu thành công';
  toast(r.message||'Đã lưu cấu hình AI');await refresh();
 }catch(err){
  if(feedback)feedback.textContent='✕ Không thể lưu: '+err.message;
  toast('Lưu cấu hình AI: '+err.message,true);
 }finally{if(button){button.disabled=false;button.textContent='Lưu cấu hình AI';}}
}
async function saveTelegramSettings(event){
 event.preventDefault();
 const form=event.target,e=new FormData(form);
 const payload={bot_token:keyValueForSave('telegramBotTokenInput'),telegram_allowed_ids:e.get('telegram_allowed_ids')||'',
 telegram_autostart:e.get('telegram_autostart')==='on'};
 try{const r=await api('settings/telegram',payload);toast(r.message||'Đã lưu Telegram');await refresh()}
 catch(err){toast(err.message,true)}
}
async function removeIntegrationSecret(provider){
 const label=provider==='gemini'?'Gemini API key':provider==='groq'?'Groq API key':provider==='claude'?'Claude API key':provider==='openai'?'OpenAI API key':'Telegram Bot Token';
 if(!confirm('Xóa '+label+' khỏi database SQLite mã hóa trên máy?'))return;
 try{const route=provider==='gemini'?'gemini/remove-key':provider==='groq'?'groq/remove-key':provider==='claude'?'claude/remove-key':provider==='openai'?'openai/remove-key':'telegram/remove-token';
 const r=await api('settings/'+route,{confirm:true});
 toast(r.message||'Đã xóa khóa đã lưu');await refresh();}
 catch(e){toast('Không xóa được '+label+': '+e.message,true)}
}
async function testConnection(target){
 const isCard=target==='gemini'||target==='groq';
 const el=isCard?$('#'+target+'ConnectionResult'):null;
 const keyField=isCard?$('#aiSettingsForm input[name="'+target+'_api_key"]'):null;
 const typed=keyField?.value?.trim()||'';
 const payload=isCard?{api_key:typed,check:true}:{check:true};
 if(el){el.hidden=false;el.classList.remove('error');el.textContent='Đang kiểm tra kết nối '+target+'...';}
 try{
  const result=await api('settings/'+target+'/test',payload);
  const info=(result.message||'Kết nối thành công')+
   (result.bot_username?' (@'+result.bot_username+')':'')+
   (result.unlisted_models?.length?' • Model chưa xuất hiện: '+result.unlisted_models.join(', '):'')+
   (result.supported_models?.length?' • Model được tài khoản hỗ trợ: '+result.supported_models.join(', '):'')+
   (result.warning?' • '+result.warning:'');
  if(el)el.textContent='✓ '+info+(typed?' Khóa vừa nhập chưa được lưu; bấm Lưu cấu hình AI để sử dụng.':'');
  else toast(info);
 }catch(e){
  if(el){el.hidden=false;el.classList.add('error');el.textContent='✕ '+e.message;}
  toast('Kiểm tra '+target+' thất bại: '+e.message,true);
 }
}
async function testGroqChat(){
 if(!confirm('Thử gọi Groq GPT-OSS-120B giống mã Python đã chạy được, bằng một câu ngắn? Phép thử tiêu thụ một ít token/quota API và có thể phát sinh phí nếu tài khoản Groq đang dùng gói trả phí.'))return;
 const el=$('#groqConnectionResult');
 const typed=$('#aiSettingsForm input[name="groq_api_key"]')?.value?.trim()||'';
 if(el){el.hidden=false;el.classList.remove('error');el.textContent='Đang gọi Groq SDK GPT-OSS-120B như mã Python mẫu...';}
 try{
  const result=await api('settings/groq/test-chat',{api_key:typed,confirm_token_use:true});
  const message='✓ '+(result.message||'Đã gọi Groq thành công')+
     (result.sample?' Phản hồi: '+result.sample:'');
  if(el)el.textContent=message;else toast(message);
 }catch(err){
  if(el){el.hidden=false;el.classList.add('error');el.textContent='✕ '+err.message;}
  toast('Thử GPT-OSS-120B như Python mẫu thất bại: '+err.message,true);
 }
}
async function testGroqSavedCEO(){
 if(!confirm('Kiểm tra API key ĐÃ LƯU trong database và model Groq AI CEO ĐÃ LƯU? Sẽ tạo một phản hồi ngắn, tiêu thụ token/quota và có thể phát sinh phí tùy gói Groq.'))return;
 const el=$('#groqConnectionResult');
 const typed=$('#groqApiKeyInput')?.value?.trim()||'';
 if(el){el.hidden=false;el.classList.remove('error');el.textContent='Đang gọi Groq bằng khóa SQLite và model AI CEO thực tế...';}
 try{
   const result=await api('settings/groq/test-saved-agent',{agent:'ceo',confirm_token_use:true});
   const msg='✓ '+(result.message||'Groq hoạt động')+' Model: '+result.model+
     (result.sample?' • Trả lời: '+result.sample:'')+
     (typed?' • Lưu ý: khóa đang nhập trong ô có thể khác khóa đã lưu trong database.':'');
   if(el)el.textContent=msg;else toast(msg);
 }catch(err){
   const msg='✕ Kiểm tra khóa đã lưu/model CEO thất bại: '+err.message+
      (typed?' • Bạn đang nhập khóa trong ô: hãy bấm Lưu cấu hình AI để dùng khóa mới.':'');
   if(el){el.hidden=false;el.classList.add('error');el.textContent=msg;}
   toast(msg,true);
 }
}
async function controlTelegram(action){
 try{
  const r=await api('settings/telegram/'+action,{action:true});
  toast(r.telegram?.message||'Đã cập nhật Bot');await refresh();
 }catch(e){toast('Telegram Bot: '+e.message,true)}
}
function domView(){const ss=data.training||[];const isActive=ss.some(s=>['starting','recording','saving'].includes(s.status));return `${pageHead('◉ BROWSER LEARNING','Học thao tác <span class="gradient-text">đăng sản phẩm</span>','Bấm bắt đầu trong phần mềm → làm mẫu trên trình duyệt → bấm dừng để lưu DOM và các bước.',eButton('◉ Bắt đầu học','onclick="showTrainForm()"'))}
 <div class="two-cols"><section class="panel"><div class="panel-head"><h3>Các phiên học thao tác</h3><small>${ss.length} phiên</small></div><div class="table-wrap">${ss.length?`<table class="data-table"><thead><tr><th>Profile</th><th>Nguồn</th><th>Trạng thái</th><th>Số thao tác</th><th>Điều khiển</th></tr></thead><tbody>${ss.map(x=>`<tr><td><strong>${h(x.account_id)}</strong><div class="tagline">${h(x.mode)}</div></td><td>${tag(x.target)}</td><td>${tag(x.status)}<div class="tagline">${h(x.message||'')}</div></td><td>${x.events_count||0}</td><td><div class="inline-actions">${['starting','recording'].includes(x.status)?`<button class="small-btn stop-btn" onclick="stopTraining('${x.id}')">■ Dừng & lưu</button>`:''}<button class="small-btn" onclick="showTrainingDetail('${x.id}')">Xem dữ liệu</button></div></td></tr>`).join('')}</tbody></table>`:empty('⌘','Chưa có phiên học','Nhấn Bắt đầu học để mở trang mẫu và ghi thao tác thủ công.')}</div></section>
 <section class="panel padded"><h3>🖱 Học bằng nút bấm</h3>${[['1','Chọn gian hàng','Chọn profile Chrome và loại công việc tạo mới/cập nhật.'],['2','Bấm Bắt đầu học','Phần mềm mở trình duyệt theo profile bạn đã đăng nhập.'],['3','Bạn thao tác mẫu','Bấm vào form, nhập dữ liệu, chọn ảnh như bình thường.'],['4','Bấm Dừng & lưu','AI lưu thẻ input/textarea/select, label và chuỗi tương tác để bạn kiểm tra.']].map(x=>`<div class="info-row"><span class="ic">${x[0]}</span><div><strong>${x[1]}</strong><p>${x[2]}</p></div></div>`).join('')}<div class="note warning" style="margin-top:15px">Mặc định học trên form demo nội bộ. Chỉ chọn Seller Center khi bạn có quyền sử dụng công cụ ghi thao tác theo điều khoản nền tảng. Không thu dữ liệu đã nhập, mật khẩu, OTP hoặc cookie. Không tự bấm đăng.</div></section></div>`}
function render(){document.querySelectorAll('.nav-item').forEach(x=>x.classList.toggle('active',x.dataset.view===activeView));$('#breadcrumb').textContent=labels[activeView];const views={hq:home,agents:agentsView,missions:missionsView,forum:forumView,video:videoRoomView,flow:flowView,settings:settingsView,shops:shopsView,proxies:proxiesView,products:productsView,jobs:jobsView,memory:memoryView,telegram:telegramView,dom:domView};$('#mainContent').innerHTML=(views[activeView]||home)();if(activeView==='hq'&&sceneMode==='mars'){if($('#marsSvg'))$('#marsSvg').style.transform=`scale(${sceneScale})`;document.querySelectorAll('.room').forEach(el=>{el.addEventListener('click',()=>el.dataset.agent?openAgent(el.dataset.agent):navigate(el.dataset.view));el.addEventListener('keydown',e=>{if(e.key==='Enter')el.click()})})}}
function openAgent(id){const a=data.agents.find(x=>x.id===id);if(!a)return;const ms=data.missions.filter(m=>m.agent_id===id);openModal(`<div class="eyebrow">PHÒNG BAN AI – CHỈ XEM</div><div style="font-size:43px;margin:14px 0">${a.emoji}</div><h2>${a.name}</h2><p class="sub">${a.room} • ${a.role}</p><div class="note">Bạn chỉ giao nhiệm vụ cho AI CEO. ${a.id==='ceo'?'AI CEO tiếp nhận và điều phối toàn bộ công việc.':'Đây là phòng ban nội bộ, nhận việc qua AI CEO khi chức năng điều phối được kích hoạt.'}</div><h3 style="margin-top:24px">Nhiệm vụ liên quan (${ms.length})</h3>${ms.length?ms.slice(0,4).map((m,i)=>miniTaskRow(m,i)).join(''):'<div class="empty-sm">Chưa có nhiệm vụ trong hàng đợi</div>'}<button class="primary-btn" style="margin-top:20px" onclick="closeModal();showMissionForm()">👑 Giao việc cho AI CEO</button>`)}
function showMissionForm(){
 openModal('<div class="eyebrow">CEO COMMAND CENTER</div><h2>Giao nhiệm vụ cho AI CEO</h2>'+
 '<p class="sub">Chủ doanh nghiệp chỉ giao việc cho AI CEO. Từ hồ sơ sản phẩm, CEO điều phối phòng nghiên cứu TikTok, biên kịch, kiểm duyệt và bàn giao sang Phòng Video AI.</p>'+
 '<form id="missionForm"><input type="hidden" name="agent_id" value="ceo">'+
 '<div class="note">👑 Người tiếp nhận duy nhất: AI CEO · không tự đăng video hoặc tạo MP4 khi chưa tích hợp công cụ render.</div>'+
 '<div class="field"><label>Loại nhiệm vụ</label><select name="workflow" id="missionWorkflow" onchange="toggleMissionWorkflow()">'+
 '<option value="tiktok_video" selected>🎯 SEO + Giá bán lẻ + Video 40s + 5 prompt Veo 3</option>'+
 '<option value="">Nhiệm vụ CEO thông thường</option></select></div>'+
 '<div class="field"><label>Tiêu đề nhiệm vụ</label><input name="title" required minlength="3" maxlength="150" placeholder="Ví dụ: Lập 3 video bán trà thảo mộc"></div>'+
 '<div class="field"><label>Yêu cầu chi tiết</label><textarea name="detail" maxlength="2000" rows="3" placeholder="Phong cách video, khách hàng mục tiêu, thông điệp, tỷ lệ khung hình..."></textarea></div>'+
 '<section id="videoMissionFields" class="video-form-fields">'+
 '<div class="video-form-grid">'+
 '<div class="field"><label>Tên sản phẩm *</label><input name="product_name" maxlength="180" required placeholder="Trà thảo mộc..."></div>'+
 '<div class="field"><label>Thành phần sản phẩm *</label><textarea name="ingredients" maxlength="2500" rows="3" required placeholder="Ghi chính xác theo nhãn sản phẩm"></textarea></div></div>'+
 '<div class="video-form-grid">'+
 '<div class="field"><label>Ảnh sản phẩm 3D (PNG/JPG/WebP, tối đa 8MB)</label><input name="image3d" type="file" accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp"><small>Ảnh chỉ làm tham chiếu; không được tự đổi chữ, màu, thiết kế bao bì.</small></div>'+
 '<div class="field"><label>Giấy tờ công bố sản phẩm (PDF/PNG/JPG/WebP, tối đa 12MB)</label><input name="disclosure_file" type="file" accept=".pdf,.png,.jpg,.jpeg,.webp,application/pdf,image/png,image/jpeg,image/webp"><small>Tài liệu được lưu cục bộ. PDF có thể trích chữ nhưng cần kiểm chứng; ảnh/scan cần xem thủ công.</small></div></div>'+
 '<div class="field"><label>Link video TikTok tham khảo (mỗi dòng một link, tối đa 8)</label><textarea name="tiktok_urls" rows="3" placeholder="https://www.tiktok.com/@.../video/..."></textarea></div>'+
 '<div class="field"><label>Giá bán lẻ đối thủ (URL + giá + ngày kiểm tra nếu có)</label><textarea name="price_evidence" maxlength="4500" rows="3" placeholder="Link đối thủ, giá được đăng và ngày kiểm tra. Để trống nếu không có nguồn."></textarea><small>Chưa có nguồn thì AI chỉ đề xuất cách khảo sát, không bịa giá.</small></div>'+
 '<div class="field"><label>Ghi chú nội dung video / transcript do bạn cung cấp</label><textarea name="research_notes" maxlength="4200" rows="3" placeholder="Ghi hook mở đầu, cách quay, lời thoại, phản ứng người xem..."></textarea><small>Phần mềm không tự tải/xem nội dung video TikTok từ URL. Link chỉ là tài liệu tham chiếu đến khi có bản ghi/transcript.</small></div></section>'+
 '<div class="form-bottom"><button class="primary-btn" id="submitMissionButton" type="submit">👑 Gửi nhiệm vụ cho CEO</button><span class="hint" id="missionUploadStatus">AI CEO sẽ nghiên cứu, viết kịch bản, kiểm duyệt rồi bàn giao storyboard (chưa render MP4).</span></div></form>');
 $('#missionForm').addEventListener('submit',submitCEOMission);
}
function toggleMissionWorkflow(){
 const on=$('#missionWorkflow')?.value==='tiktok_video';
 const panel=$('#videoMissionFields');if(!panel)return;
 panel.hidden=!on;
 panel.querySelectorAll('[name="product_name"],[name="ingredients"]').forEach(el=>el.required=on);
}
function fileAsBase64(file,limit,kind){
 if(!file)return Promise.resolve(null);
 if(file.size>limit)throw Error(kind+' vượt dung lượng cho phép');
 return new Promise((resolve,reject)=>{
  const reader=new FileReader();
  reader.onerror=()=>reject(Error('Không thể đọc tệp '+kind));
  reader.onload=()=>{
   const s=String(reader.result||'');
   const base64=s.includes(',')?s.slice(s.indexOf(',')+1):'';
   resolve({name:file.name,type:file.type,base64});
  };
  reader.readAsDataURL(file);
 });
}
async function submitCEOMission(event){
 event.preventDefault();
 const form=event.currentTarget, fd=new FormData(form);
 const video=fd.get('workflow')==='tiktok_video';
 const b=$('#submitMissionButton'),msg=$('#missionUploadStatus');
 b.disabled=true;b.textContent='Đang lưu nhiệm vụ...';
 try{
  const payload={agent_id:'ceo',title:String(fd.get('title')||''),
    detail:String(fd.get('detail')||''),workflow:video?'tiktok_video':''};
  if(video){
   payload.product_name=String(fd.get('product_name')||'');
   payload.ingredients=String(fd.get('ingredients')||'');
   payload.tiktok_urls=String(fd.get('tiktok_urls')||'');
   payload.research_notes=String(fd.get('research_notes')||'');
   payload.price_evidence=String(fd.get('price_evidence')||'');
   const image=fd.get('image3d'),paper=fd.get('disclosure_file');
   if(image instanceof File&&image.name)
    payload.image3d=await fileAsBase64(image,8*1024*1024,'Ảnh sản phẩm');
   if(paper instanceof File&&paper.name)
    payload.disclosure_file=await fileAsBase64(paper,12*1024*1024,'Giấy công bố');
  }
  if(msg)msg.textContent='Đang chuyển hồ sơ sản phẩm vào database cục bộ...';
  const ctrl=new AbortController();
  const timer=setTimeout(()=>ctrl.abort(),90000);
  let response;
  try{
   response=await fetch('/api/missions',{method:'POST',
    headers:{'Content-Type':'application/json'},credentials:'same-origin',
    body:JSON.stringify(payload),signal:ctrl.signal});
  }finally{clearTimeout(timer)}
  const result=await response.json();
  if(!response.ok||!result.ok)throw Error(result.error||'Không thể lưu nhiệm vụ');
  closeModal();
  toast('Đã gửi hồ sơ cho CEO. Phòng nghiên cứu và Phòng Video AI sẽ hiển thị trạng thái.');
  await refresh();
 }catch(err){
  if(msg)msg.textContent='Lỗi: '+(err.name==='AbortError'?'Quá thời gian tải lên':err.message);
  toast('Không lưu được hồ sơ: '+err.message,true);
 }finally{b.disabled=false;b.textContent='👑 Gửi nhiệm vụ cho CEO';}
}
function showCEOReport(id){
 const m=data.missions.find(x=>x.id===id);
 if(!m)return;
 const statusText={pending:'Chờ CEO tiếp nhận',in_progress:'CEO đang điều phối',done:'CEO đã lập báo cáo',blocked:'Bị chặn – cần xử lý lỗi'};
 const steps=m.delegations||[];
 const warnings=m.ceo_error?`<div class="note warning">${h(m.ceo_error)}</div>`:'';
 const rows=steps.map(x=>`<div class="info-row"><span class="ic">♟</span><div><strong>${h(x.agent_id)} – ${h(x.status)}</strong><p style="white-space:pre-wrap">${h((x.result||x.error||'Đang xử lý').slice(0,2400))}</p></div></div>`).join('');
 const stepsHtml=rows||'<div class="empty-sm">CEO đang lập kế hoạch hoặc chưa giao việc</div>';
 const retryButton=m.status==='blocked'?`<button class="primary-btn" style="margin-top:20px" onclick="closeModal();retryCEOTask(${m.id})">↻ Thử lại nhiệm vụ</button>`:'';
 openModal(`<div class="eyebrow">CEO COMMAND CENTER • #${m.id}</div>
 <h2>${h(m.title)}</h2><p class="sub">👑 AI CEO • ${h(statusText[m.status]||m.status)}</p>
 ${warnings}<h3 style="margin:18px 0 10px">Phòng ban CEO đã phân công (${steps.length} bản ghi)</h3>
 ${stepsHtml}<h3 style="margin:22px 0 10px">Báo cáo AI CEO</h3>
 <div class="note" style="white-space:pre-wrap">${h(m.ceo_report||m.ceo_plan||'CEO chưa có báo cáo. Hãy xem trạng thái Ollama.').slice(0,16000)}</div>
 <button class="small-btn" style="margin-top:15px" onclick="openForum(${m.id})">◉ Xem toàn bộ log thảo luận</button>${retryButton}`);
}
async function retryCEOTask(id){try{await api('missions/retry',{id});closeModal();toast('Đã đưa nhiệm vụ về hàng đợi CEO');await refresh()}catch(e){toast(e.message,true)}}
function showShopForm(){openModal(`<div class="eyebrow">MULTI-SHOP HUB</div><h2>Thêm Chrome Profile</h2><p class="sub">Tạo profile riêng; chọn proxy đã nhập ở Kho Proxy.</p><form id="shopForm"><div class="field"><label>ID tài khoản (không dấu, không khoảng trắng)</label><input name="id" required pattern="[a-z0-9][a-z0-9_-]{1,39}" placeholder="shopee_01"></div><div class="field"><label>Tên hiển thị</label><input name="name" required placeholder="Shop trà thảo mộc 01"></div><div class="field"><label>Nền tảng</label><select name="platform"><option value="shopee">Shopee</option><option value="tiktok">TikTok Shop</option></select></div><div class="field"><label>Proxy sử dụng</label><select name="proxy_id"><option value="">Không sử dụng proxy</option>${(data.proxies||[]).map(p=>`<option value="${h(p.id)}">${h(p.name)} (${h(p.host)}:${p.port})</option>`).join('')}</select></div><div class="note">Muốn thêm proxy mới? Đóng cửa sổ này và chọn <b>Kho Proxy → Thêm proxy</b>.</div><div class="form-bottom"><button class="primary-btn">Tạo profile</button></div></form>`);$('#shopForm').addEventListener('submit',async e=>{e.preventDefault();await submitForm('accounts',e.target)})}
function showProxyForm(pid=''){
 const p=data.proxies.find(p=>p.id===pid),edit=!!p;
 openModal(`<div class="eyebrow">PROXY MANAGER</div><h2>${edit?'Sửa proxy':'Thêm proxy bằng tay'}</h2><p class="sub">Điền thông tin trực tiếp. Mật khẩu (nếu có) được giữ trong kho mật khẩu hệ điều hành.</p><form id="proxyForm">
 <div class="field"><label>Mã proxy</label><input name="id" pattern="[a-z][a-z0-9_-]{1,39}" value="${h(p?.id||'')}" ${edit?'readonly':''} required placeholder="proxy_01"></div>
 <div class="field"><label>Tên hiển thị</label><input name="name" value="${h(p?.name||'')}" required placeholder="Proxy Shopee miền Bắc"></div>
 <div class="field"><label>Loại kết nối</label><select name="scheme">${['http','https','socks5'].map(x=>`<option value="${x}" ${p?.scheme===x?'selected':''}>${x.toUpperCase()}</option>`).join('')}</select></div>
 <div class="two-fields"><div class="field"><label>IP / Hostname</label><input name="host" value="${h(p?.host||'')}" required placeholder="192.0.2.10"></div><div class="field"><label>Port</label><input type="number" name="port" min="1" max="65535" value="${p?.port||''}" required placeholder="8080"></div></div>
 <div class="field"><label>Username (để trống nếu proxy không cần xác thực)</label><input name="username" autocomplete="off" value="${h(p?.username||'')}"></div>
 <div class="field"><label>Mật khẩu proxy ${edit?'(để trống nếu không thay đổi)':''}</label><input name="password" type="password" autocomplete="new-password" placeholder="Không hiển thị lại mật khẩu đã lưu"></div>
 <div class="note warning">Không nhập cookie hoặc mật khẩu Shopee/TikTok Shop tại đây. Không sử dụng proxy để né các biện pháp xác minh của nền tảng.</div>
 <div class="form-bottom"><button class="primary-btn">${edit?'Lưu thay đổi':'Thêm proxy'}</button></div></form>`);
 $('#proxyForm').addEventListener('submit',async e=>{e.preventDefault();await submitForm(edit?'proxies/update':'proxies',e.target)});
}
async function checkShopSession(aid){
 try{
  const r=await api('accounts/check-session',{account_id:aid});
  toast(r.message||'Đã yêu cầu kiểm tra đăng nhập');
  await refresh();
 }catch(e){toast('Kiểm tra đăng nhập: '+e.message,true)}
}
function showAssignProxy(aid){const a=data.accounts.find(x=>x.id===aid);if(!a)return;openModal(`<div class="eyebrow">PROFILE SETTINGS</div><h2>Gán proxy • ${h(a.name)}</h2><p class="sub">Bạn cần đóng Chrome profile trước khi thay đổi proxy.</p><form id="assignProxyForm"><div class="field"><label>Chọn proxy</label><select name="proxy_id"><option value="">Không sử dụng proxy</option>${(data.proxies||[]).map(p=>`<option value="${h(p.id)}" ${a.proxy_id===p.id?'selected':''}>${h(p.name)} — ${h(p.host)}:${p.port}</option>`).join('')}</select></div><div class="form-bottom"><button class="primary-btn">Lưu gán proxy</button></div></form>`);$('#assignProxyForm').addEventListener('submit',async e=>{e.preventDefault();const fields=Object.fromEntries(new FormData(e.target));try{await api('accounts/assign-proxy',{account_id:aid,...fields});closeModal();toast('Đã cập nhật proxy của profile');await refresh()}catch(ex){toast(ex.message,true)}})}
async function testProxy(pid){try{const r=await api('proxies/test',{id:pid});toast(r.message,!r.reachable)}catch(e){toast(e.message,true)}}
async function deleteProxy(pid){if(!confirm(`Xóa proxy ${pid}? Cần gỡ khỏi các profile trước.`))return;try{await api('proxies/delete',{id:pid});toast('Đã xóa proxy');await refresh()}catch(e){toast(e.message,true)}}
function showTrainForm(selectedAid=''){
 const ac=data.accounts||[];
 openModal(`<div class="eyebrow">LEARNING MODE</div><h2>Bắt đầu học đăng bài</h2><p class="sub">Nhấn nút để mở Chrome; thao tác như bình thường rồi nhấn Dừng & lưu ở màn hình Học đăng bài.</p><form id="trainForm"><div class="field"><label>Chrome Profile</label><select name="account_id" required>${ac.length?ac.map(a=>`<option value="${h(a.id)}" ${selectedAid===a.id?'selected':''}>${h(a.name)} (${h(a.platform)})</option>`).join(''):'<option value="">Hãy tạo gian hàng trước</option>'}</select></div><div class="field"><label>Quy trình</label><select name="mode"><option value="new">Đăng sản phẩm mới</option><option value="update">Cập nhật sản phẩm</option></select></div><div class="field"><label>Nguồn học</label><select name="target" id="trainTarget"><option value="demo">Form demo nội bộ (khuyến nghị để thử)</option><option value="seller">Trang Seller Center (chỉ khi được phép)</option></select></div><label class="checkbox-line"><input type="checkbox" name="permission_confirmed" value="yes"> Tôi xác nhận có quyền dùng công cụ ghi thao tác trên trang đã chọn.</label><div class="note">Chỉ ghi các sự kiện bấm/chọn và metadata DOM, không ghi nội dung bạn gõ. Khi hoàn thành, trở lại phần mềm và nhấn <b>Dừng & lưu</b>.</div><div class="form-bottom"><button class="primary-btn" ${ac.length?'':'disabled'}>◉ Bắt đầu học</button></div></form>`);
 $('#trainForm').addEventListener('submit',async e=>{e.preventDefault();const body=Object.fromEntries(new FormData(e.target));body.permission_confirmed=body.permission_confirmed==='yes';try{const r=await api('training/start',body);closeModal();navigate('dom');toast('Đã yêu cầu mở Chrome ghi thao tác');await refresh()}catch(ex){toast(ex.message,true)}})
}
async function stopTraining(id){if(!confirm('Dừng ghi và lưu các bước đã thao tác?'))return;try{await api('training/stop',{id});toast('Đang lưu bản ghi');await refresh()}catch(e){toast(e.message,true)}}
async function showTrainingDetail(id){try{const v=await api('training/detail?id='+id);const rows=(v.steps||[]).slice(0,90);const fields=(v.fields||[]).slice(0,70);openModal(`<div class="eyebrow">DOM TRAINING</div><h2>Chi tiết phiên học</h2><p class="sub">${rows.length} thao tác hiển thị • ${fields.length} trường DOM • Chưa duyệt để tự chạy.</p><h3>Các thao tác của bạn</h3><div class="scroll-steps">${rows.map((r,i)=>`<div class="step-row"><b>${i+1}. ${h(r.action)} • ${h(r.tag)}</b><div>${h(r.label||r.aria_label||r.placeholder||r.name||r.text||r.id||'Không có nhãn')}</div></div>`).join('')||'<p>Chưa ghi được thao tác nào.</p>'}</div><h3 style="margin-top:20px">Các trường phát hiện</h3><div class="scroll-steps">${fields.map(r=>`<div class="step-row"><b>${h(r.tag)} ${h(r.suggested_field||'')}</b><div>${h(r.label||r.placeholder||r.name||r.id||'Không có nhãn')}</div></div>`).join('')||'<p>Chưa có bản kiểm kê DOM. Hãy Dừng & lưu.</p>'}</div><div class="note warning" style="margin-top:15px">Dữ liệu học này không tự thực hiện đăng sản phẩm. Cần kiểm tra và xác nhận ánh xạ các trường trước khi phát triển công cụ điền form.</div>`)}catch(ex){toast(ex.message,true)}}
function showProductForm(){openModal(`<div class="eyebrow">PRODUCT LIBRARY</div><h2>Tạo hồ sơ sản phẩm</h2><p class="sub">Thông tin được sử dụng khi soạn nhiệm vụ đăng sản phẩm.</p><form id="productForm"><div class="field"><label>SKU</label><input name="sku" required placeholder="TRA-DINHLANG-01"></div><div class="field"><label>Tên sản phẩm</label><input name="title" required maxlength="200"></div><div class="field"><label>Mô tả đã được kiểm tra</label><textarea name="description" required></textarea></div><div class="field"><label>Giá bán (VND)</label><input type="number" name="price" min="0" step="1" required></div><div class="field"><label>Tồn kho</label><input type="number" name="stock" min="0" step="1" required></div><div class="form-bottom"><button class="primary-btn">Lưu sản phẩm</button></div></form>`);$('#productForm').addEventListener('submit',async e=>{e.preventDefault();await submitForm('products',e.target,{numbers:['price','stock']})})}
function showLearningForm(){openModal(`<div class="eyebrow">LONG TERM MEMORY</div><h2>Thêm bài học</h2><p class="sub">Bài học mới được đánh dấu chưa xác minh.</p><form id="learningForm"><div class="field"><label>Nhóm kiến thức</label><select name="category"><option value="marketing">Marketing</option><option value="shop">Gian hàng</option><option value="dom">DOM / UI</option><option value="compliance">Pháp lý</option><option value="campaign">Chiến dịch</option></select></div><div class="field"><label>Tiêu đề</label><input name="title" required></div><div class="field"><label>Chi tiết</label><textarea name="description" required></textarea></div><div class="field"><label>Nguồn (nếu có)</label><input name="source" placeholder="URL hoặc mã thử nghiệm"></div><div class="form-bottom"><button class="primary-btn">Lưu kiến thức</button></div></form>`);$('#learningForm').addEventListener('submit',async e=>{e.preventDefault();await submitForm('learnings',e.target)})}
function showJobForm(){const ac=data.accounts;const skus=Object.keys(data.products);openModal(`<div class="eyebrow">LISTING QUEUE</div><h2>Yêu cầu AI CEO đăng sản phẩm</h2><p class="sub">Lệnh được gửi cho CEO, không chuyển trực tiếp sang phòng ban hay trình duyệt.</p><form id="jobForm"><div class="field"><label>SKU</label><select name="sku" required>${skus.map(s=>`<option value="${h(s)}">${h(s)}</option>`).join('')}</select></div><div class="field"><label>Shop/Profile</label><select name="account_id" required>${ac.length?ac.map(a=>`<option value="${h(a.id)}">${h(a.name)} (${a.platform})</option>`).join(''):'<option value="">Chưa có shop - hãy tạo trước</option>'}</select></div><div class="field"><label>Loại công việc</label><select name="mode"><option value="new">Đăng sản phẩm mới</option><option value="update">Cập nhật sản phẩm</option></select></div><div class="note warning">Sau khi tạo job, gửi ảnh vào Telegram bằng <code>ADD=ID</code> hoặc sử dụng công cụ nhập ảnh cũ. Không tự đăng bài từ màn hình này.</div><div class="form-bottom"><button class="primary-btn" ${!ac.length?'disabled':''}>Gửi yêu cầu đến CEO</button></div></form>`);$('#jobForm').addEventListener('submit',async e=>{e.preventDefault();await submitForm('jobs',e.target)})}
async function submitForm(endpoint,form,opts={}){const payload=Object.fromEntries(new FormData(form).entries());for(const field of opts.numbers||[])payload[field]=Number(payload[field]);try{await api(endpoint,payload);closeModal();toast(endpoint==='jobs'?'Đã gửi yêu cầu đăng sản phẩm cho AI CEO (chưa tạo job hoặc đăng bài)':'Đã lưu nhiệm vụ cho AI CEO');await refresh()}catch(e){toast(e.message,true)}}
async function openProfile(id){if(!confirm(`Mở Chrome Profile ${id}? Hãy đăng nhập thủ công và tuân thủ chính sách của sàn.`))return;try{const x=await api('open-profile',{account_id:id});toast(x.message)}catch(e){toast(e.message,true)}}

async function approveJob(id){if(!confirm(`Duyệt nhiệm vụ #${id}? Phải có ảnh, giá và tồn kho đã xác minh.`))return;try{await api('jobs/approve',{id});toast('Đã duyệt nhiệm vụ');await refresh()}catch(e){toast(e.message,true)}}
async function rejectJob(id){if(!confirm(`Từ chối nhiệm vụ #${id}?`))return;try{await api('jobs/reject',{id});toast('Đã từ chối');await refresh()}catch(e){toast(e.message,true)}}
function copyText(t){if(navigator.clipboard?.writeText)navigator.clipboard.writeText(t).then(()=>toast('Đã sao chép')).catch(()=>toast('Không thể sao chép',true));else toast('Trình duyệt chưa hỗ trợ sao chép',true)}
$('#nav').addEventListener('click',e=>{const b=e.target.closest('[data-view]');if(b)navigate(b.dataset.view)});
$('#mobileMenuButton').addEventListener('click',()=>setMobileMenu(!document.body.classList.contains('menu-open')));
$('#sidebarBackdrop').addEventListener('click',()=>setMobileMenu(false));
window.addEventListener('resize',()=>{if(window.innerWidth>920)setMobileMenu(false)});
$('#refreshBtn').addEventListener('click',refresh);
$('#closeModal').addEventListener('click',closeModal);
$('#modalBackdrop').addEventListener('click',e=>{if(e.target.id==='modalBackdrop')closeModal()});
window.addEventListener('keydown',e=>{if(e.key!=='Escape')return;if(document.body.classList.contains('menu-open'))setMobileMenu(false);else closeModal()});
setInterval(()=>{if(['dom','missions','hq','shops'].includes(activeView)&&$('#modalBackdrop')?.hidden&&document.visibilityState==='visible')refresh()},9000);
setInterval(()=>{if(activeView==='forum'&&document.visibilityState==='visible')loadForum()},6500);
setInterval(()=>{$('#clock').textContent=new Date().toLocaleString('vi-VN',{hour:'2-digit',minute:'2-digit',day:'2-digit',month:'2-digit'})},1000);
refresh();

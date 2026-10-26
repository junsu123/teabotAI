/* TEA AI Mars Studio GUI. All mutations are initiated explicitly by the user. */
const h = x => String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const $ = s => document.querySelector(s);
let data={agents:[],accounts:[],jobs:[],missions:[],learnings:[],products:{},proxies:[],training:[],stats:{}}, activeView='hq', focusAgent=null, sceneScale=1, sceneMode='mars';
let forumMissionId=0,forumData=null,forumBusy=false;
const labels={hq:'Trụ sở AI',agents:'Nhân viên AI',missions:'Giao nhiệm vụ CEO',forum:'Phòng họp AI',shops:'Gian hàng & Profile',proxies:'Kho Proxy',products:'Kho sản phẩm',jobs:'Đơn đăng sản phẩm',memory:'Bộ nhớ tự học',telegram:'Telegram Bot',settings:'Cài đặt ChatGPT & Telegram',dom:'Học đăng bài'};
async function api(endpoint, body=null){
 const ctrl=new AbortController(), timer=setTimeout(()=>ctrl.abort(),endpoint==='overview'?6000:endpoint.endsWith('/test')?20000:12000);
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
function navigate(view){activeView=view;focusAgent=null;render();document.querySelector('#mainContent').scrollTo({top:0});if(view==='forum')loadForum()}
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
 ${pageHead('◈ MARS OPERATIONS','Trụ sở <span class="gradient-text">TEA AI Company</span>','Một trụ sở ảo cho toàn bộ đội AI marketing trà túi lọc.',eButton('👑 Giao việc cho CEO','onclick="showMissionForm()"'))}
 <div class="metrics">
  ${[['♟','Nhân viên AI',s.agents||6,'Đã cấu hình'],['▣','Tài khoản shop',s.shops||0,'Profile riêng từng shop'],['◫','Nhiệm vụ đăng',s.jobs_open||0,'Đang xử lý / chờ duyệt'],['✧','Bài học đã lưu',s.lessons||0,'Kho ký ức dùng chung']].map(x=>`<div class="metric"><span class="metric-icon">${x[0]}</span><div class="metric-label">${x[1]}</div><div class="metric-value">${x[2]}</div><div class="metric-caption">${x[3]}</div></div>`).join('')}
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
 <h3>✦ Chế độ API miễn phí – Gemini chính, Groq phụ</h3>
 <p class="tagline">Thiết lập trực tiếp: Gemini là AI chính, Groq dự phòng. Claude, OpenAI và Ollama vẫn có thể chọn. Chỉ AI CEO quyết định cuối.</p>
 <form id="aiSettingsForm" onsubmit="saveAISettings(event)">
 <label class="checkbox-line" style="margin:14px 0;padding:12px;border:1px solid #315062;border-radius:10px">
 <input type="checkbox" name="free_only" onchange="updateFreeOnlyControls()" ${cfg.free_only!==false?'checked':''}>
 <strong>Chỉ sử dụng model có gói API miễn phí (khuyên dùng)</strong></label>
 <div class="note">Gemini Free Tier và Groq Free Plan tùy tài khoản, hạn mức và trạng thái thanh toán. Tùy chọn này chặn Claude/OpenAI, nhưng không bảo đảm tài khoản Gemini/Groq đã bật billing sẽ không phát sinh phí.</div>
 <div class="field"><label>Gemini API Key (Google AI Studio) – ƯU TIÊN CHÍNH</label>
 <input name="gemini_api_key" type="password" autocomplete="new-password" placeholder="${cfg.gemini_key_configured?'Đã lưu Gemini key – để trống để giữ nguyên':'Dán Gemini API key tại đây'}"></div>
 <div class="field"><label>Groq API Key – DỰ PHÒNG</label>
 <input name="groq_api_key" type="password" autocomplete="new-password" placeholder="${cfg.groq_key_configured?'Đã lưu Groq key – để trống để giữ nguyên':'Dán Groq API key tại đây'}"></div>
 <div class="form-bottom" style="display:flex;flex-wrap:wrap;gap:8px">
 <button type="button" class="small-btn" onclick="testConnection('gemini')">✓ Kiểm tra Gemini</button>
 <button type="button" class="small-btn" onclick="testConnection('groq')">✓ Kiểm tra Groq</button>
 <button type="button" class="small-btn" onclick="removeIntegrationSecret('gemini')" ${cfg.gemini_key_configured?'':'disabled'}>Xóa Gemini key</button>
 <button type="button" class="small-btn" onclick="removeIntegrationSecret('groq')" ${cfg.groq_key_configured?'':'disabled'}>Xóa Groq key</button></div>
 <div id="groqConnectionResult" class="note" role="status" aria-live="polite">
 Bấm Kiểm tra Groq để xác minh ngay cả khi chưa lưu key. Nếu thành công, hãy bấm Lưu cấu hình AI để sử dụng khóa.</div>
 <div class="note">Thứ tự ưu tiên: <strong>Gemini → Groq → Claude → OpenAI → Ollama</strong>.
 Trong chế độ TỰ ĐỘNG, Claude và OpenAI chỉ được thử nếu bạn cho phép API trả phí. Không có giới hạn đảm bảo miễn phí: quota tùy tài khoản Google/Groq.</div>
 <label class="checkbox-line"><input type="checkbox" name="allow_paid_fallback" ${cfg.allow_paid_fallback?'checked':''} ${cfg.free_only!==false?'disabled':''}>
 Cho phép tự chuyển sang Claude/OpenAI trả phí khi Gemini/Groq tạm gián đoạn</label>
 <div class="field"><label>Claude API Key (Anthropic)</label>
 <input type="password" name="claude_api_key" autocomplete="new-password" placeholder="${cfg.claude_key_configured?'Đã lưu khóa Claude – để trống nếu không thay đổi':'Nhập Claude API key tại đây'}">
 <small>${cfg.claude_key_configured?'✓ Đã lưu Claude API key trong Windows':'Chưa cấu hình Claude API key'}</small></div>
 <div class="field"><label>Ngân sách Claude tháng (USD, chỉ là giới hạn ước tính cục bộ)</label>
 <input name="claude_monthly_limit_usd" type="number" min="0.5" max="1000" step="0.5" value="${Number(cfg.claude_monthly_limit_usd||12)}"></div>
 <div class="field"><label>OpenAI API key – chỉ dùng khi bạn chọn OpenAI</label>
 <input type="password" name="openai_api_key" autocomplete="new-password" placeholder="${cfg.openai_key_configured?'Đã lưu khóa OpenAI – để trống nếu không đổi':'Không bắt buộc khi chỉ dùng Claude'}">
 <small>${cfg.openai_key_configured?'✓ Đã lưu OpenAI key':'Chưa lưu OpenAI key'}</small></div>
 <div class="field"><label>Ngân sách OpenAI tháng (USD)</label>
 <input name="monthly_limit_usd" type="number" min="0.5" max="1000" step="0.5" value="${Number(cfg.monthly_limit_usd||12)}"></div>
 <div class="note">Model Free Tier mặc định: Gemini 3.8 Flash cho CEO/Strategy/Research/Compliance, Gemini 3.5 Flash-Lite cho Creative/Analyst; Groq GPT-OSS 120B và 20B. Claude/OpenAI là API trả phí, không thuộc chế độ miễn phí.</div>
 <div class="form-bottom" style="margin:10px 0"><button type="button" class="small-btn" onclick="preferFreePreset()">✦ Áp dụng Gemini → Groq cho tất cả agent</button><button type="button" class="small-btn" onclick="preferClaudePreset()">✦ Ưu tiên Claude cho tất cả agent</button>
 <button type="button" class="small-btn" onclick="preferBalancedPreset()">◉ Claude CEO & chiến lược, Ollama việc nhẹ</button></div>
 <div class="table-wrap"><table class="data-table"><thead><tr><th>Vị trí</th><th>Nhà cung cấp</th><th>Model Gemini</th><th>Model Groq</th><th>Model Claude</th><th>Model OpenAI</th></tr></thead>
 <tbody>${roles.map(a=>{
 const provider=providers[a]||'auto';
 return `<tr><td><strong>${agentName[a]}</strong></td>
 <td><select name="provider_${a}">
 ${[['auto','Tự động: Gemini → Groq → Ollama'],['gemini','Gemini (có Free Tier)'],['groq','Groq (có Free Plan)'],['claude','Claude (trả phí)'],['openai','OpenAI (trả phí)'],['ollama','Ollama cục bộ']].map(p=>`<option value="${p[0]}" ${p[0]===provider?'selected':''} ${cfg.free_only!==false&&['claude','openai'].includes(p[0])?'disabled':''}>${p[1]}</option>`).join('')}
 </select></td>
 <td><select name="gemini_model_${a}">${['gemini-3.8-flash','gemini-3.6-flash','gemini-3.5-flash-lite','gemini-3.1-flash-lite','gemini-2.5-flash','gemini-2.5-flash-lite'].map(m=>`<option value="${m}" ${m===(cfg.gemini_models?.[a]||(a==='creative'||a==='analyst'?'gemini-3.5-flash-lite':'gemini-3.8-flash'))?'selected':''}>${m}</option>`).join('')}</select></td>
 <td><select name="groq_model_${a}">${['openai/gpt-oss-120b','openai/gpt-oss-20b','qwen/qwen3.8-27b'].map(m=>`<option value="${m}" ${m===(cfg.groq_models?.[a]||(a==='creative'||a==='analyst'?'openai/gpt-oss-20b':'openai/gpt-oss-120b'))?'selected':''}>${m}</option>`).join('')}</select></td>
 <td><select name="claude_model_${a}">
 ${['claude-sonnet-4-6','claude-opus-4-6','claude-haiku-4-5'].map(m=>`<option value="${m}" ${m===(claudeModels[a]||'claude-sonnet-4-6')?'selected':''}>${m}</option>`).join('')}
 </select></td>
 <td><select name="openai_model_${a}">
 ${['gpt-6.1-sol','gpt-6-luna'].map(m=>`<option value="${m}" ${m===(openaiModels[a]||'gpt-6-luna')?'selected':''}>${m}</option>`).join('')}
 </select></td></tr>`}).join('')}</tbody></table></div>
 <div class="form-bottom" style="display:flex;gap:8px;flex-wrap:wrap">
 <button type="submit" class="primary-btn">💾 Lưu cấu hình AI</button>
 <button type="button" class="small-btn" onclick="testConnection('claude')">✓ Kiểm tra Claude API</button>
 <button type="button" class="small-btn" onclick="testConnection('openai')">✓ Kiểm tra OpenAI API</button>
 <button type="button" class="small-btn" onclick="removeIntegrationSecret('claude')" ${cfg.claude_key_configured?'':'disabled'}>Xóa Claude key</button>
 <button type="button" class="small-btn" onclick="removeIntegrationSecret('openai')" ${cfg.openai_key_configured?'':'disabled'}>Xóa OpenAI key</button>
 </div>
 </form>
 <div class="note">Chi phí ước tính tháng này — Claude: ${Number(data.claude_usage?.estimated_usd||0).toFixed(4)} USD (${Number(data.claude_usage?.calls||0)} lượt); OpenAI: ${Number(data.openai_usage?.estimated_usd||0).toFixed(4)} USD (${Number(data.openai_usage?.calls||0)} lượt).
 Chỉ thay đổi lựa chọn mô hình cho lượt gọi AI tiếp theo, không ảnh hưởng phiên đang xử lý.</div>
 </section>`;
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
 for(const a of ['ceo','strategy','compliance','research','creative','analyst'])
   form.elements['provider_'+a].value='auto';
 form.elements['free_only'].checked=true;
 form.elements['allow_paid_fallback'].checked=false;
 updateFreeOnlyControls();
 toast('Đã chọn Gemini → Groq → Ollama, chặn Claude/OpenAI trả phí. Bấm Lưu để áp dụng.');
}
function preferClaudePreset(){
 const form=$('#aiSettingsForm');if(!form)return;
 if(form.elements['free_only'].checked){toast('Hãy tắt Chỉ sử dụng model có gói miễn phí trước khi chọn Claude.',true);return;}
 for(const a of ['ceo','strategy','compliance','research','creative','analyst']){
   form.elements['provider_'+a].value='claude';
   form.elements['claude_model_'+a].value=['creative','analyst'].includes(a)?'claude-haiku-4-5':'claude-sonnet-4-6';
 }
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
 toast('Đã chọn Claude cho CEO/Strategy/Compliance. Bấm Lưu để áp dụng.');
}
function telegramSettingsSection(){
 const cfg=data.connection_settings||{},bot=data.telegram_process||{};
 return `<section class="panel padded"><h3>➤ Cài đặt Telegram Bot</h3>
 <p class="tagline">Lưu token, ID người được phép và điều khiển Bot bằng nút trên giao diện.</p>
 <form id="telegramSettingsForm" onsubmit="saveTelegramSettings(event)">
 <div class="field"><label>Bot Token (tạo bằng @BotFather)</label>
 <input type="password" name="bot_token" autocomplete="new-password"
 placeholder="${cfg.telegram_token_configured?'Đã lưu token – để trống để giữ nguyên':'Dán bot token ở đây'}">
 <small>${cfg.telegram_token_configured?'✓ Có token được lưu trong Windows':'Chưa lưu Telegram Bot Token'}</small></div>
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
function settingsView(){return `${pageHead('⚙ LOCAL INTEGRATIONS','Cài đặt <span class="gradient-text">Gemini / Groq / AI & Telegram</span>',
 'Cấu hình trực tiếp tại đây – không sửa file .env và không chạy lệnh cấu hình.', '')}
 <div class="two-cols">${aiSettingsSection()}${telegramSettingsSection()}</div>`;}
function telegramView(){return `${pageHead('➤ TELEGRAM CONNECTOR','Telegram <span class="gradient-text">Bot</span>',
 'Thiết lập và vận hành bot nhận ảnh ngay trong phần mềm.',eButton('⚙ Cài đặt cả ChatGPT','onclick="navigate(\'settings\')"'))}
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
  gemini_api_key:e.get('gemini_api_key')||'',groq_api_key:e.get('groq_api_key')||'',
  claude_api_key:e.get('claude_api_key')||'',openai_api_key:e.get('openai_api_key')||'',
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
 try{const r=await api('settings/ai',payload);toast(r.message||'Đã lưu cấu hình AI');await refresh()}
 catch(err){toast('Lưu cấu hình AI: '+err.message,true)}
}
async function saveTelegramSettings(event){
 event.preventDefault();
 const form=event.target,e=new FormData(form);
 const payload={bot_token:e.get('bot_token')||'',telegram_allowed_ids:e.get('telegram_allowed_ids')||'',
 telegram_autostart:e.get('telegram_autostart')==='on'};
 try{const r=await api('settings/telegram',payload);toast(r.message||'Đã lưu Telegram');await refresh()}
 catch(err){toast(err.message,true)}
}
async function removeIntegrationSecret(provider){
 const label=provider==='gemini'?'Gemini API key':provider==='groq'?'Groq API key':provider==='claude'?'Claude API key':provider==='openai'?'OpenAI API key':'Telegram Bot Token';
 if(!confirm('Xóa '+label+' khỏi kho mật khẩu Windows?'))return;
 try{const route=provider==='gemini'?'gemini/remove-key':provider==='groq'?'groq/remove-key':provider==='claude'?'claude/remove-key':provider==='openai'?'openai/remove-key':'telegram/remove-token';
 const r=await api('settings/'+route,{confirm:true});
 toast(r.message||'Đã xóa khóa đã lưu');await refresh();}
 catch(e){toast('Không xóa được '+label+': '+e.message,true)}
}
async function testConnection(target){
 const el=target==='groq'?$('#groqConnectionResult'):null;
 const typed=target==='groq'?($('#aiSettingsForm input[name="groq_api_key"]')?.value||''):'';
 const payload=target==='groq'?{api_key:typed,check:true}:{check:true};
 if(el)el.textContent='Đang liên hệ GroqCloud qua HTTPS và kiểm tra key...';
 try{
  const r=await api('settings/'+target+'/test',payload);
  let info=(r.message||'Kết nối thành công')+
    (r.bot_username?' (@'+r.bot_username+')':'')+
    (r.unlisted_models?.length?' • Model chưa xuất hiện: '+r.unlisted_models.join(', '):'')+
    (r.supported_models?.length?' • Model khả dụng: '+r.supported_models.join(', '):'')+
    (r.warning?' • '+r.warning:'');
  if(el){
   el.textContent='✓ '+info+(typed?' Khóa vừa nhập chưa được lưu; bấm Lưu cấu hình AI để sử dụng.':'');
  }else toast(info);
 }catch(e){
  if(el)el.textContent='✕ '+e.message;
  toast('Kiểm tra '+target+' thất bại: '+e.message,true);
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
function render(){document.querySelectorAll('.nav-item').forEach(x=>x.classList.toggle('active',x.dataset.view===activeView));$('#breadcrumb').textContent=labels[activeView];const views={hq:home,agents:agentsView,missions:missionsView,forum:forumView,settings:settingsView,shops:shopsView,proxies:proxiesView,products:productsView,jobs:jobsView,memory:memoryView,telegram:telegramView,dom:domView};$('#mainContent').innerHTML=(views[activeView]||home)();if(activeView==='hq'&&sceneMode==='mars'){if($('#marsSvg'))$('#marsSvg').style.transform=`scale(${sceneScale})`;document.querySelectorAll('.room').forEach(el=>{el.addEventListener('click',()=>el.dataset.agent?openAgent(el.dataset.agent):navigate(el.dataset.view));el.addEventListener('keydown',e=>{if(e.key==='Enter')el.click()})})}}
function openAgent(id){const a=data.agents.find(x=>x.id===id);if(!a)return;const ms=data.missions.filter(m=>m.agent_id===id);openModal(`<div class="eyebrow">PHÒNG BAN AI – CHỈ XEM</div><div style="font-size:43px;margin:14px 0">${a.emoji}</div><h2>${a.name}</h2><p class="sub">${a.room} • ${a.role}</p><div class="note">Bạn chỉ giao nhiệm vụ cho AI CEO. ${a.id==='ceo'?'AI CEO tiếp nhận và điều phối toàn bộ công việc.':'Đây là phòng ban nội bộ, nhận việc qua AI CEO khi chức năng điều phối được kích hoạt.'}</div><h3 style="margin-top:24px">Nhiệm vụ liên quan (${ms.length})</h3>${ms.length?ms.slice(0,4).map((m,i)=>miniTaskRow(m,i)).join(''):'<div class="empty-sm">Chưa có nhiệm vụ trong hàng đợi</div>'}<button class="primary-btn" style="margin-top:20px" onclick="closeModal();showMissionForm()">👑 Giao việc cho AI CEO</button>`)}
function showMissionForm(){openModal(`<div class="eyebrow">CEO COMMAND CENTER</div><h2>Giao nhiệm vụ cho AI CEO</h2><p class="sub">Bạn chỉ trao đổi với AI CEO. CEO sẽ phân tích, lập kế hoạch, phân công cho các phòng ban và báo cáo về cho bạn khi quy trình điều phối AI được kết nối.</p><form id="missionForm"><input type="hidden" name="agent_id" value="ceo"><div class="note">👑 Người tiếp nhận duy nhất: <b>AI CEO</b></div><div class="field"><label>Tiêu đề nhiệm vụ</label><input name="title" required minlength="3" placeholder="Ví dụ: Phân tích kế hoạch bán trà đinh lăng" maxlength="150"></div><div class="field"><label>Yêu cầu chi tiết</label><textarea name="detail" maxlength="2000" placeholder="Mục tiêu, sản phẩm, nền tảng, thời hạn..."></textarea></div><div class="form-bottom"><button class="primary-btn">Gửi nhiệm vụ cho CEO</button><span class="hint">Hiện chỉ lưu vào hàng đợi; CEO tự điều phối chưa được kích hoạt.</span></div></form>`);$('#missionForm').addEventListener('submit',async e=>{e.preventDefault();await submitForm('missions',e.target)})}
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
$('#nav').addEventListener('click',e=>{const b=e.target.closest('[data-view]');if(b)navigate(b.dataset.view)});$('#refreshBtn').addEventListener('click',refresh);$('#closeModal').addEventListener('click',closeModal);$('#modalBackdrop').addEventListener('click',e=>{if(e.target.id==='modalBackdrop')closeModal()});window.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal()});
setInterval(()=>{if(['dom','missions','hq','shops'].includes(activeView)&&$('#modalBackdrop')?.hidden&&document.visibilityState==='visible')refresh()},9000);
setInterval(()=>{if(activeView==='forum'&&document.visibilityState==='visible')loadForum()},6500);
setInterval(()=>{$('#clock').textContent=new Date().toLocaleString('vi-VN',{hour:'2-digit',minute:'2-digit',day:'2-digit',month:'2-digit'})},1000);
refresh();

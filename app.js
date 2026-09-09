const SHEET_ID = '1Rq_D6v9maRHbCG-jzCkwPz0EJpAuw5JZXzaPAhZ5lU8';
const FOLLOWER_SHEET_ID = SHEET_ID;
const FOLLOWER_SHEET_NAME = '주간 팔로워 추적';
const channels = [
  { key:'x', label:'X', gid:'767840176', metric:'조회수', accent:'#171916' },
  { key:'blog', label:'블로그', gid:'985504785', metric:'조회수', accent:'#62b35a' },
  { key:'instagram', label:'인스타그램', gid:'1290540291', metric:'조회수', accent:'#ef6c84' },
  { key:'clip', label:'네이버 클립', gid:'38881012', metric:'조회수', accent:'#16c46b' },
  { key:'tiktok', label:'틱톡', gid:'234211931', metric:'조회수', accent:'#36c5d7' },
  { key:'youtube', label:'유튜브', gid:'1166931392', metric:'조회수', accent:'#f04438' }
];

let allData = []; let activeChannel = 'all'; let followerData = [];
const columnsByChannel = {};
const excludedColumns = new Set(['키워드', '필수 해시태그']);
const $ = (s) => document.querySelector(s);
const fmt = new Intl.NumberFormat('ko-KR');

function parseDate(value){
  if (!value) return null;
  const text = String(value).trim();
  const googleDate = text.match(/^Date\((\d{4}),(\d{1,2}),(\d{1,2})\)$/);
  if (googleDate) return new Date(Number(googleDate[1]), Number(googleDate[2]), Number(googleDate[3]));
  const short = text.match(/^(\d{2})\s*[.\/-]\s*(\d{1,2})\s*[.\/-]\s*(\d{1,2})$/);
  if (short) return new Date(2000+Number(short[1]), Number(short[2])-1, Number(short[3]));
  const match = text.match(/(\d{4})\s*[.\/-]\s*(\d{1,2})\s*[.\/-]\s*(\d{1,2})/);
  if (!match) return null;
  return new Date(Number(match[1]), Number(match[2])-1, Number(match[3]));
}
function iso(date){ return date ? `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}` : ''; }
function displayDate(date){ return date ? `${date.getFullYear()}.${String(date.getMonth()+1).padStart(2,'0')}.${String(date.getDate()).padStart(2,'0')}` : '—'; }
function escapeHtml(v=''){ return String(v).replace(/[&<>'"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
function toNumber(value){ return Number(String(value??'').replace(/[^0-9.-]/g,''))||0; }

async function loadSheet(channel){
  const url = `https://docs.google.com/spreadsheets/d/${SHEET_ID}/gviz/tq?tqx=out:json&gid=${channel.gid}&headers=1&_=${Date.now()}`;
  const text = await fetch(url).then(r=>{ if(!r.ok) throw new Error(r.status); return r.text(); });
  const json = JSON.parse(text.slice(text.indexOf('{'), text.lastIndexOf('}')+1));
  const headers = json.table.cols.map(c => c.label || '');
  columnsByChannel[channel.key] = headers.filter((h,i) => h && !excludedColumns.has(h) && headers.indexOf(h) === i);
  return json.table.rows.map(row => {
    const obj = {}; headers.forEach((h,i)=>{ if(h && obj[h] === undefined) obj[h] = row.c[i]?.v ?? ''; });
    const title = obj['콘텐츠 이름(제목)'] || obj['콘텐츠 이름']; const link = obj['콘텐츠 링크'];
    if (!title && !link) return null;
    const likes=toNumber(obj['좋아요수']); const comments=toNumber(obj['댓글수']); const other=toNumber(obj['그 외 반응수'] ?? obj['그 외 반응 수']);
    const views=toNumber(obj[channel.metric]);
    return { channel:channel.key, channelLabel:channel.label, date:parseDate(obj['업로드 날짜']), contentId:String(obj['콘텐츠 ID']||'').trim(), product:String(obj['제품 모델']||'').trim(), format:String(obj['콘텐츠 형식']||'').trim(), title:title || '(제목 없음)', topic:obj['콘텐츠 주제'] || '미분류', owner:obj['담당자'] || '—', link:link || '', views, likes, comments, other, reactions:likes+comments+other, reactionRate:views?(likes+comments+other)/views:0, raw:obj };
  }).filter(Boolean);
}

async function loadGviz(spreadsheetId, params){
  const url = `https://docs.google.com/spreadsheets/d/${spreadsheetId}/gviz/tq?tqx=out:json&headers=1&${params}&_=${Date.now()}`;
  const text = await fetch(url).then(r=>{ if(!r.ok) throw new Error(r.status); return r.text(); });
  const json = JSON.parse(text.slice(text.indexOf('{'), text.lastIndexOf('}')+1));
  const headers = json.table.cols.map(c=>String(c.label||'').replace(/\s+/g,' ').trim());
  return json.table.rows.map(row=>{ const obj={}; headers.forEach((h,i)=>{ if(h&&obj[h]===undefined) obj[h]=row.c[i]?.v??''; }); return obj; });
}

async function loadFollowers(){
  const rows = await loadGviz(FOLLOWER_SHEET_ID, `sheet=${encodeURIComponent(FOLLOWER_SHEET_NAME)}`);
  if(!rows.length) throw new Error('empty follower sheet');
  return rows.map(r=>({
    date:parseDate(r['날짜'] || r['줌']), platform:String(r['플랫폼']||'').trim(),
    followers:toNumber(r['팔로워(구독자) 수'] ?? r['팔로워수']),
    followerDelta:toNumber(r['전주 대비 구독자증감량'] ?? r['구독자증감량']),
    inflow:toNumber(r['스토어 유입수'] ?? r['스토어유입수']),
    inflowDelta:toNumber(r['전주 대비 유입수 증감량'] ?? r['유입수증감량'])
  })).filter(r=>r.date&&r.platform);
}

function isNumericColumn(name){ return /수$|전환$/.test(name); }
function cellValue(row, column){
  if(column === '채널' || column === '플랫폼') return row.channelLabel;
  if(column === '업로드 날짜') return displayDate(row.date);
  if(column === '제품 모델') return row.product;
  if(column === '콘텐츠 형식') return row.format;
  if(column === '콘텐츠 ID') return row.contentId;
  if(column === '반응률') return row.reactionRate;
  if(column === '콘텐츠 이름' || column === '콘텐츠 이름(제목)') return row.title;
  return row.raw?.[column] ?? '';
}
function renderCell(row, column){
  const value = cellValue(row,column);
  if(column === '콘텐츠 링크') return row.link ? `<a class="view-link" href="${escapeHtml(row.link.trim())}" target="_blank" rel="noopener">열기 ↗</a>` : '—';
  if(column === '콘텐츠 주제') return `<span class="topic-tag">${escapeHtml(value || '미분류')}</span>`;
  if(column === '콘텐츠 이름' || column === '콘텐츠 이름(제목)') return escapeHtml(value || '(제목 없음)');
  if(column === '반응률') return `${(row.reactionRate*100).toFixed(2)}%`;
  if(isNumericColumn(column)) return fmt.format(Number(value) || 0);
  return escapeHtml(value || '—');
}
function renderSummaryRow(rows, columns){
  return `<tr class="summary-row">${columns.map((column,index)=>{
    const numeric = isNumericColumn(column) || column === '조회수' || column === '반응률';
    let content = '—';
    if(column === '반응률'){
      const views=rows.reduce((sum,row)=>sum+row.views,0), reactions=rows.reduce((sum,row)=>sum+row.reactions,0);
      content = `<strong>${views?(reactions/views*100).toFixed(2):'0.00'}%</strong>`;
    } else if(numeric){
      const total = rows.reduce((sum,row)=>sum+(column==='조회수' ? row.views : Number(cellValue(row,column))||0),0);
      content = `<strong>${fmt.format(total)}</strong>`;
    } else if(column === '콘텐츠 이름' || column === '콘텐츠 이름(제목)') content = `<strong>기간 합계 · ${fmt.format(rows.length)}건</strong>`;
    else if(index === 0 && !columns.some(c=>c==='콘텐츠 이름'||c==='콘텐츠 이름(제목)')) content = `<strong>기간 합계 · ${fmt.format(rows.length)}건</strong>`;
    else if(column === '채널') content = `<strong>${fmt.format(rows.length)}건</strong>`;
    return `<td class="${numeric?'number-cell':''}">${content}</td>`;
  }).join('')}</tr>`;
}

function filteredData(){
  const start = parseDate($('#startDate').value); const end = parseDate($('#endDate').value);
  return allData.filter(item => (!start || (item.date && item.date >= start)) && (!end || (item.date && item.date <= end)));
}
function applyWorkFilters(rows){
  const platform=$('#platformFilter').value||'all', product=$('#productFilter').value||'all', format=$('#formatFilter').value||'all';
  return rows.filter(row=>(platform==='all'||row.channel===platform)&&(product==='all'||row.product===product)&&(format==='all'||row.format===format));
}
function sortWorkRows(rows){
  const mode=$('#sortSelect').value;
  return [...rows].sort((a,b)=>mode==='views_desc'?b.views-a.views:mode==='views_asc'?a.views-b.views:mode==='er_desc'?b.reactionRate-a.reactionRate:mode==='er_asc'?a.reactionRate-b.reactionRate:(b.date||0)-(a.date||0));
}
function sumMetrics(rows){ const views=rows.reduce((s,r)=>s+r.views,0); return {count:rows.length,views,avg:rows.length?Math.round(views/rows.length):0}; }
function shiftDays(date,days){ const d=new Date(date); d.setDate(d.getDate()+days); return d; }
function shiftMonth(date,months){ const d=new Date(date); const day=d.getDate(); d.setDate(1); d.setMonth(d.getMonth()+months); d.setDate(Math.min(day,new Date(d.getFullYear(),d.getMonth()+1,0).getDate())); return d; }
function between(rows,start,end){ return rows.filter(r=>r.date&&r.date>=start&&r.date<=end); }
function rate(current,previous){ if(previous===0) return current===0?0:null; return (current-previous)/previous; }
function trendHtml(current,previous){ const value=rate(current,previous); if(value===null) return '<span class="trend flat">신규</span>'; const cls=value>0?'up':value<0?'down':'flat'; const arrow=value>0?'▲':value<0?'▼':'—'; return `<span class="trend ${cls}">${arrow}${value===0?'':Math.abs(value*100).toFixed(0)+'%'}</span>`; }
function metricCompare(label,current,previous){ return `<span class="compare-value">${fmt.format(current)}${trendHtml(current,previous)}</span>`; }
function comparisonFor(rows,anchor,type){
  let currentStart,currentEnd=anchor,previousStart,previousEnd;
  if(type==='week'){
    currentStart=shiftDays(anchor,-6); previousEnd=shiftDays(currentStart,-1); previousStart=shiftDays(previousEnd,-6);
  }else{
    currentStart=new Date(anchor.getFullYear(),anchor.getMonth(),1); previousEnd=shiftDays(currentStart,-1); previousStart=new Date(previousEnd.getFullYear(),previousEnd.getMonth(),1);
  }
  return {current:sumMetrics(between(rows,currentStart,currentEnd)),previous:sumMetrics(between(rows,previousStart,previousEnd))};
}
function latestDate(rows){ return rows.map(r=>r.date).filter(Boolean).sort((a,b)=>b-a)[0]||null; }

function audiencePeriod(){
  const start=parseDate($('#startDate').value), end=parseDate($('#endDate').value);
  return followerData.filter(r=>(!start||r.date>=start)&&(!end||r.date<=end));
}
function followerSnapshot(){
  const periodRows=audiencePeriod();
  const platforms=[...new Set(followerData.map(r=>r.platform))];
  return platforms.map(platform=>{
    const rows=periodRows.filter(r=>r.platform===platform).sort((a,b)=>b.date-a.date);
    if(!rows.length) return null;
    return {platform,followers:rows[0].followers,delta:rows.reduce((s,r)=>s+r.followerDelta,0),date:rows[0].date};
  }).filter(Boolean);
}
function storeSnapshot(){
  const rows=audiencePeriod();
  if(!rows.length) return null;
  return {inflow:rows.reduce((s,r)=>s+r.inflow,0),delta:rows.reduce((s,r)=>s+r.inflowDelta,0),latest:latestDate(rows)};
}
function aggregateById(rows){
  const map=new Map();
  rows.filter(r=>r.contentId).forEach(r=>{
    if(!map.has(r.contentId)) map.set(r.contentId,{id:r.contentId,rows:[],views:0,likes:0,comments:0,other:0,reactions:0,platforms:new Set()});
    const item=map.get(r.contentId); item.rows.push(r); item.views+=r.views; item.likes+=r.likes; item.comments+=r.comments; item.other+=r.other; item.reactions+=r.reactions; item.platforms.add(r.channelLabel);
  });
  return [...map.values()];
}
function chooseContentId(id){ $('#idSearch').value=id; renderIdComparison(); $('#idPerformance').scrollIntoView({behavior:'smooth',block:'center'}); }
function renderRankList(title,items,metric){
  return `<article class="rank-card"><h3>${title}</h3>${items.slice(0,5).map((item,i)=>`<div class="rank-row"><span>${i+1}</span><button type="button" data-content-id="${escapeHtml(item.id)}">${escapeHtml(item.id)}</button><strong>${fmt.format(item[metric])}</strong></div>`).join('')||'<p class="section-note">집계할 콘텐츠 ID가 없습니다.</p>'}</article>`;
}
function renderIdComparison(){
  const aggregates=aggregateById(filteredData());
  const viewsRank=[...aggregates].sort((a,b)=>b.views-a.views); const reactionsRank=[...aggregates].sort((a,b)=>b.reactions-a.reactions);
  $('#idRankings').innerHTML=renderRankList('총조회수 TOP 콘텐츠 ID',viewsRank,'views')+renderRankList('총반응수 TOP 콘텐츠 ID',reactionsRank,'reactions');
  document.querySelectorAll('[data-content-id]').forEach(button=>button.onclick=()=>chooseContentId(button.dataset.contentId));
  const query=$('#idSearch').value.trim().toLowerCase();
  if(!query){ $('#idPerformance').innerHTML='<p class="id-empty">콘텐츠 ID를 검색하면 여러 플랫폼에 업로드된 동일 콘텐츠의 통합 성과를 확인할 수 있습니다.</p>'; return; }
  const exact=aggregates.find(item=>item.id.toLowerCase()===query); const matches=aggregates.filter(item=>item.id.toLowerCase().includes(query));
  if(!exact&&matches.length!==1){
    $('#idPerformance').innerHTML=matches.length?`<div class="id-empty">일치하는 콘텐츠 ID를 선택해 주세요.<div class="id-match-list">${matches.slice(0,12).map(item=>`<button type="button" data-id-match="${escapeHtml(item.id)}">${escapeHtml(item.id)}</button>`).join('')}</div></div>`:'<p class="id-empty">선택한 기간에 일치하는 콘텐츠 ID가 없습니다.</p>';
    document.querySelectorAll('[data-id-match]').forEach(button=>button.onclick=()=>chooseContentId(button.dataset.idMatch)); return;
  }
  const item=exact||matches[0]; const platformMap=new Map();
  item.rows.forEach(r=>{ if(!platformMap.has(r.channelLabel)) platformMap.set(r.channelLabel,{platform:r.channelLabel,views:0,reactions:0}); const p=platformMap.get(r.channelLabel); p.views+=r.views; p.reactions+=r.reactions; });
  const platforms=[...platformMap.values()].sort((a,b)=>b.views-a.views); const maxViews=Math.max(...platforms.map(p=>p.views),1);
  $('#idPerformance').innerHTML=`<div class="id-result"><div class="id-result-head"><div><p>검색 결과</p><h3>${escapeHtml(item.id)}</h3></div><p>${escapeHtml(item.rows[0]?.title||'')}</p></div><div class="id-summary"><article class="id-summary-card"><span>업로드 플랫폼 수</span><strong>${fmt.format(item.platforms.size)}</strong></article><article class="id-summary-card"><span>총조회수</span><strong>${fmt.format(item.views)}</strong></article><article class="id-summary-card"><span>총반응수</span><strong>${fmt.format(item.reactions)}</strong><small>좋아요 ${fmt.format(item.likes)} + 댓글 ${fmt.format(item.comments)} + 그 외 ${fmt.format(item.other)}</small></article></div><article class="platform-compare"><h3>플랫폼별 도달·반응 효율</h3>${platforms.map(p=>`<div class="platform-row"><strong>${escapeHtml(p.platform)}</strong><div class="platform-bar"><i style="width:${(p.views/maxViews*100).toFixed(1)}%"></i></div><span>조회 ${fmt.format(p.views)}</span><span class="platform-rate">반응률 ${p.views?(p.reactions/p.views*100).toFixed(2):'0.00'}%</span></div>`).join('')}</article></div>`;
}
function aggregateByProduct(rows){
  const map=new Map();
  rows.filter(r=>r.product&&r.product!=='없음').forEach(r=>{
    const key=r.product.toLowerCase().replace(/\s+/g,' ').trim();
    if(!map.has(key)) map.set(key,{key,name:r.product,rows:[],views:0,likes:0,comments:0,other:0,reactions:0,platforms:new Set()});
    const item=map.get(key); item.rows.push(r); item.views+=r.views; item.likes+=r.likes; item.comments+=r.comments; item.other+=r.other; item.reactions+=r.reactions; item.platforms.add(r.channelLabel);
  });
  return [...map.values()];
}
function chooseProduct(name){ $('#productSearch').value=name; renderProductComparison(); $('#productPerformance').scrollIntoView({behavior:'smooth',block:'center'}); }
function renderProductRankList(title,items,metric){
  return `<article class="rank-card"><h3>${title}</h3>${items.slice(0,5).map((item,i)=>`<div class="rank-row"><span>${i+1}</span><button type="button" data-product-name="${escapeHtml(item.name)}">${escapeHtml(item.name)}</button><strong>${fmt.format(item[metric])}</strong></div>`).join('')||'<p class="section-note">집계할 제품이 없습니다.</p>'}</article>`;
}
function renderProductComparison(){
  const aggregates=aggregateByProduct(filteredData());
  $('#productRankings').innerHTML=renderProductRankList('총조회수 TOP 제품', [...aggregates].sort((a,b)=>b.views-a.views),'views')+renderProductRankList('총반응수 TOP 제품',[...aggregates].sort((a,b)=>b.reactions-a.reactions),'reactions');
  document.querySelectorAll('[data-product-name]').forEach(button=>button.onclick=()=>chooseProduct(button.dataset.productName));
  const query=$('#productSearch').value.trim().toLowerCase().replace(/\s+/g,' ');
  if(!query){ $('#productPerformance').innerHTML='<p class="id-empty">제품 모델을 검색하면 여러 플랫폼과 콘텐츠의 통합 성과를 확인할 수 있습니다.</p>'; return; }
  const exact=aggregates.find(item=>item.key===query); const matches=aggregates.filter(item=>item.key.includes(query));
  if(!exact&&matches.length!==1){
    $('#productPerformance').innerHTML=matches.length?`<div class="id-empty">일치하는 제품을 선택해 주세요.<div class="id-match-list">${matches.slice(0,12).map(item=>`<button type="button" data-product-match="${escapeHtml(item.name)}">${escapeHtml(item.name)}</button>`).join('')}</div></div>`:'<p class="id-empty">선택한 기간에 일치하는 제품 모델이 없습니다.</p>';
    document.querySelectorAll('[data-product-match]').forEach(button=>button.onclick=()=>chooseProduct(button.dataset.productMatch)); return;
  }
  const item=exact||matches[0]; const platformMap=new Map();
  item.rows.forEach(r=>{ if(!platformMap.has(r.channelLabel)) platformMap.set(r.channelLabel,{platform:r.channelLabel,views:0,reactions:0,count:0}); const p=platformMap.get(r.channelLabel); p.views+=r.views; p.reactions+=r.reactions; p.count+=1; });
  const platforms=[...platformMap.values()].sort((a,b)=>b.views-a.views); const maxViews=Math.max(...platforms.map(p=>p.views),1);
  $('#productPerformance').innerHTML=`<div class="id-result"><div class="id-result-head"><div><p>제품 검색 결과</p><h3>${escapeHtml(item.name)}</h3></div><p>${fmt.format(item.rows.length)}개 콘텐츠 통합</p></div><div class="id-summary"><article class="id-summary-card"><span>업로드 플랫폼 수</span><strong>${fmt.format(item.platforms.size)}</strong></article><article class="id-summary-card"><span>발행 콘텐츠</span><strong>${fmt.format(item.rows.length)}</strong></article><article class="id-summary-card"><span>총조회수</span><strong>${fmt.format(item.views)}</strong></article><article class="id-summary-card"><span>총반응수</span><strong>${fmt.format(item.reactions)}</strong><small>좋아요 ${fmt.format(item.likes)} + 댓글 ${fmt.format(item.comments)} + 그 외 ${fmt.format(item.other)}</small></article></div><article class="platform-compare"><h3>플랫폼별 제품 성과</h3>${platforms.map(p=>`<div class="platform-row"><strong>${escapeHtml(p.platform)}</strong><div class="platform-bar"><i style="width:${(p.views/maxViews*100).toFixed(1)}%"></i></div><span>조회 ${fmt.format(p.views)}</span><span class="platform-rate">반응률 ${p.views?(p.reactions/p.views*100).toFixed(2):'0.00'}%</span></div>`).join('')}</article></div>`;
}
function renderAudience(){
  const followers=followerSnapshot(); const store=storeSnapshot();
  const followerCard=`<article class="audience-card"><h3>플랫폼별 팔로워 · 구독자</h3><div class="follower-list">${followers.length?followers.map(item=>`<div class="follower-item"><span>${escapeHtml(item.platform)} · ${displayDate(item.date)}</span><strong>${fmt.format(item.followers)}</strong><span class="trend ${item.delta>0?'up':item.delta<0?'down':'flat'}">${item.delta>0?'▲':item.delta<0?'▼':'—'}${item.delta===0?'':fmt.format(Math.abs(item.delta))}</span></div>`).join(''):'<p class="section-note">조회 기간의 팔로워 데이터가 없습니다.</p>'}</div></article>`;
  const storeCard=`<article class="audience-card"><h3>스토어 유입수</h3>${store?`<strong class="store-value">${fmt.format(store.inflow)}</strong><div class="store-trends"><span>유입수 증감량 <b class="trend ${store.delta>0?'up':store.delta<0?'down':'flat'}">${store.delta>0?'▲':store.delta<0?'▼':'—'}${store.delta===0?'':fmt.format(Math.abs(store.delta))}</b></span></div><p class="kpi-note">선택 기간 합계 · 최신 ${displayDate(store.latest)}</p>`:'<p class="section-note">조회 기간의 유입 데이터가 없습니다.</p>'}</article>`;
  const warning=followers.length?'':'<p class="source-warning">‘주간 팔로워 추적’ 시트가 현재 콘텐츠 원본 파일에서 확인되지 않아 팔로워 값은 보류되었습니다. 해당 시트가 있는 Google Sheets 링크를 연결하면 자동 반영됩니다.</p>';
  $('#audienceGrid').innerHTML=followerCard+storeCard+warning;
}
function comparisonDates(start,end,mode){
  if(mode==='week') return {start:shiftDays(start,-7),end:shiftDays(end,-7)};
  if(mode==='same_month') return {start:shiftMonth(start,-1),end:shiftMonth(end,-1)};
  const previousEnd=new Date(start.getFullYear(),start.getMonth(),0);
  return {start:new Date(previousEnd.getFullYear(),previousEnd.getMonth(),1),end:previousEnd};
}
function renderPeriodComparison(){
  const start=parseDate($('#startDate').value), end=parseDate($('#endDate').value), mode=$('#compareMode').value;
  if(!start||!end||mode==='none'){ $('#periodComparison').innerHTML='<p class="section-note">조회 시작일과 종료일을 설정하고 비교 기간을 선택하면 변화가 표시됩니다.</p>'; return; }
  const previous=comparisonDates(start,end,mode), currentRows=applyWorkFilters(between(allData,start,end)), previousRows=applyWorkFilters(between(allData,previous.start,previous.end));
  const current=sumMetrics(currentRows), prior=sumMetrics(previousRows);
  const cards=[['발행 콘텐츠',current.count,prior.count],['총조회수',current.views,prior.views],['평균 조회수',current.avg,prior.avg]];
  $('#periodComparison').innerHTML=`<div class="compare-summary"><div class="compare-period"><strong>선택 기간 vs 비교 기간</strong><span>${displayDate(start)}–${displayDate(end)} / ${displayDate(previous.start)}–${displayDate(previous.end)}</span></div>${cards.map(([label,value,old])=>`<div class="compare-stat"><span>${label}</span><strong>${fmt.format(value)}</strong>${trendHtml(value,old)}<small>비교값 ${fmt.format(old)}</small></div>`).join('')}</div>`;
}
function render(){
  const scoped = filteredData();
  $('#kpiGrid').innerHTML = channels.map((ch,i)=>{
    const rows=scoped.filter(r=>r.channel===ch.key); const total=sumMetrics(rows); const allRows=allData.filter(r=>r.channel===ch.key);
    const anchor=parseDate($('#endDate').value)||latestDate(allRows)||new Date(); const week=comparisonFor(allRows,anchor,'week'); const month=comparisonFor(allRows,anchor,'month');
    return `<article class="kpi-card" style="--accent:${ch.accent}"><div class="kpi-top"><span class="channel">${ch.label}</span><span class="channel-index">0${i+1}</span></div><div class="metric-grid"><div class="metric-item"><span>발행 콘텐츠</span><strong>${fmt.format(total.count)}</strong></div><div class="metric-item"><span>총조회수</span><strong>${fmt.format(total.views)}</strong></div><div class="metric-item"><span>콘텐츠당 평균 조회수</span><strong>${fmt.format(total.avg)}</strong></div></div><div class="compare-list"><div class="compare-row"><span></span><span class="compare-label">발행 콘텐츠</span><span class="compare-label">총조회수</span><span class="compare-label">평균 조회수</span></div><div class="compare-row"><span class="compare-label">전주</span>${metricCompare('count',week.current.count,week.previous.count)}${metricCompare('views',week.current.views,week.previous.views)}${metricCompare('avg',week.current.avg,week.previous.avg)}</div><div class="compare-row"><span class="compare-label">전월</span>${metricCompare('count',month.current.count,month.previous.count)}${metricCompare('views',month.current.views,month.previous.views)}${metricCompare('avg',month.current.avg,month.previous.avg)}</div></div><p class="kpi-note">증감률은 ${displayDate(anchor)} 기준</p><i class="accent-line"></i></article>`;
  }).join('');
  const rows = sortWorkRows(applyWorkFilters(scoped));
  $('#resultCount').textContent = `총 ${fmt.format(rows.length)}건`;
  const columns = ['플랫폼','업로드 날짜','제품 모델','콘텐츠 형식','콘텐츠 ID','콘텐츠 이름','콘텐츠 주제','조회수','반응률','콘텐츠 링크'];
  $('#contentHead').innerHTML = columns.map(c=>`<th class="${isNumericColumn(c)||c==='조회수'||c==='반응률'?'number-cell':''}">${c}</th>`).join('');
  const summaryRow = rows.length ? renderSummaryRow(rows,columns) : '';
  $('#contentRows').innerHTML = summaryRow + rows.map(r=>`<tr>${columns.map(c=>{
    const classes=[c==='업로드 날짜'?'date':'',c==='콘텐츠 이름'||c==='콘텐츠 이름(제목)'?'content-title':'',isNumericColumn(c)||c==='조회수'||c==='반응률'?'number-cell':''].filter(Boolean).join(' ');
    const content = c==='조회수' ? fmt.format(r.views) : renderCell(r,c);
    return `<td class="${classes}">${content}</td>`;
  }).join('')}</tr>`).join('');
  $('#emptyState').hidden = rows.length>0; $('table').hidden = rows.length===0;
  const start=$('#startDate').value, end=$('#endDate').value;
  $('#periodLabel').textContent = start||end ? `${start||'처음'} — ${end||'현재'}` : '전체 업로드 기간';
  renderAudience();
  renderIdComparison();
  renderProductComparison();
  renderPeriodComparison();
}
function renderTabs(){
  $('#tabs').innerHTML=[{key:'all',label:'전체'},...channels].map(c=>`<button class="tab ${c.key===activeChannel?'active':''}" data-channel="${c.key}" role="tab">${c.label}</button>`).join('');
  document.querySelectorAll('.tab').forEach(btn=>btn.onclick=()=>{activeChannel=btn.dataset.channel;$('#platformFilter').value=activeChannel;renderTabs();render();});
}
function setRange(type){
  const dates=allData.map(x=>x.date).filter(Boolean).sort((a,b)=>a-b); const max=dates.at(-1)||new Date(); let start=new Date(max); let end=max;
  if(type==='month') start=new Date(max.getFullYear(),max.getMonth(),1); else start.setDate(start.getDate()-Number(type)+1);
  $('#startDate').value=iso(start); $('#endDate').value=iso(end); render();
}
async function init(){
  $('#kpiGrid').innerHTML='<div class="loading-card"></div><div class="loading-card"></div><div class="loading-card"></div>';
  renderTabs();
  try {
    const results=await Promise.all(channels.map(loadSheet)); allData=results.flat();
    const extras=await Promise.allSettled([loadFollowers()]);
    followerData=extras[0].status==='fulfilled'?extras[0].value:[];
    $('#contentIdOptions').innerHTML=[...new Set(allData.map(r=>r.contentId).filter(Boolean))].sort().map(id=>`<option value="${escapeHtml(id)}"></option>`).join('');
    const products=[...new Set(allData.map(r=>r.product).filter(v=>v&&v!=='없음'))].sort((a,b)=>a.localeCompare(b,'ko'));
    const formats=[...new Set(allData.map(r=>r.format).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'ko'));
    $('#productOptions').innerHTML=products.map(value=>`<option value="${escapeHtml(value)}"></option>`).join('');
    $('#platformFilter').innerHTML='<option value="all">전체 플랫폼</option>'+channels.map(ch=>`<option value="${ch.key}">${ch.label}</option>`).join('');
    $('#productFilter').innerHTML='<option value="all">전체 제품</option>'+products.map(value=>`<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join('');
    $('#formatFilter').innerHTML='<option value="all">전체 형식</option>'+formats.map(value=>`<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join('');
    const state=$('.sync-state'); state.classList.add('ok'); $('#syncText').textContent=`시트 연동 완료 · ${new Date().toLocaleTimeString('ko-KR',{hour:'2-digit',minute:'2-digit'})}`;
    render();
  } catch(error) {
    $('.sync-state').classList.add('error'); $('#syncText').textContent='시트 연결을 확인해 주세요';
    $('#kpiGrid').innerHTML='<p>Google Sheets 데이터를 불러오지 못했습니다. 공유 설정을 확인해 주세요.</p>'; console.error(error);
  }
}
['startDate','endDate'].forEach(id=>$('#'+id).addEventListener('change',render));
$('#resetButton').onclick=()=>{$('#startDate').value='';$('#endDate').value='';render();};
document.querySelectorAll('[data-range]').forEach(b=>b.onclick=()=>setRange(b.dataset.range));
$('#idSearch').addEventListener('input',renderIdComparison);
$('#idClear').onclick=()=>{$('#idSearch').value='';renderIdComparison();};
$('#productSearch').addEventListener('input',renderProductComparison);
$('#productClear').onclick=()=>{$('#productSearch').value='';renderProductComparison();};
['productFilter','formatFilter','sortSelect','compareMode'].forEach(id=>$('#'+id).addEventListener('change',render));
$('#platformFilter').addEventListener('change',()=>{activeChannel=$('#platformFilter').value;renderTabs();render();});
const AUTH_HASH='50773fc7b2590164adfadc22ca2d0c9ba7777772a8f7f2ce5ce4ce44613b8cfd';
async function passwordHash(value){ const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value)); return [...new Uint8Array(bytes)].map(b=>b.toString(16).padStart(2,'0')).join(''); }
function unlockDashboard(){ document.body.classList.remove('locked'); $('#authGate').hidden=true; sessionStorage.setItem('contentDashboardAuth','ok'); }
if(sessionStorage.getItem('contentDashboardAuth')==='ok') unlockDashboard();
$('#authForm').addEventListener('submit',async event=>{ event.preventDefault(); const valid=await passwordHash($('#authPassword').value)===AUTH_HASH; if(valid){ unlockDashboard(); }else{ $('#authError').hidden=false; $('#authPassword').select(); } });
init();

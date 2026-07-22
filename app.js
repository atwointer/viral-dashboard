const SHEET_ID = '17JHKjuOtd3EWxylrIgk9XucOMJa8mRqAobEK2J8Fu8A';
const channels = [
  { key:'x', label:'X', sheet:'(DB)X 콘텐츠', metric:'누적 노출수', accent:'#171916' },
  { key:'blog', label:'블로그', sheet:'(DB)블로그 콘텐츠 ', metric:'누적 조회수', accent:'#62b35a' },
  { key:'instagram', label:'인스타그램', sheet:'(DB)인스타그램 콘텐츠', metric:'누적 조회수', accent:'#ef6c84' },
  { key:'clip', label:'네이버 클립', sheet:'(DB)네이버클립 콘텐츠', metric:'누적 조회수', accent:'#16c46b' },
  { key:'tiktok', label:'틱톡', sheet:'(DB)틱톡 콘텐츠', metric:'누적 조회수', accent:'#36c5d7' },
  { key:'youtube', label:'유튜브', sheet:'(DB)유튜브 콘텐츠', metric:'누적 조회수', accent:'#f04438' }
];

let allData = []; let activeChannel = 'all';
const columnsByChannel = {};
const excludedColumns = new Set(['키워드', '필수 해시태그']);
const $ = (s) => document.querySelector(s);
const fmt = new Intl.NumberFormat('ko-KR');

function parseDate(value){
  if (!value) return null;
  const match = String(value).trim().match(/(\d{4})[.\/-]\s*(\d{1,2})[.\/-]\s*(\d{1,2})/);
  if (!match) return null;
  return new Date(Number(match[1]), Number(match[2])-1, Number(match[3]));
}
function iso(date){ return date ? `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}` : ''; }
function displayDate(date){ return date ? `${date.getFullYear()}.${String(date.getMonth()+1).padStart(2,'0')}.${String(date.getDate()).padStart(2,'0')}` : '—'; }
function escapeHtml(v=''){ return String(v).replace(/[&<>'"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }

async function loadSheet(channel){
  const url = `https://docs.google.com/spreadsheets/d/${SHEET_ID}/gviz/tq?tqx=out:json&sheet=${encodeURIComponent(channel.sheet)}&headers=1`;
  const text = await fetch(url).then(r=>{ if(!r.ok) throw new Error(r.status); return r.text(); });
  const json = JSON.parse(text.slice(text.indexOf('{'), text.lastIndexOf('}')+1));
  const headers = json.table.cols.map(c => c.label || '');
  columnsByChannel[channel.key] = headers.filter((h,i) => h && !excludedColumns.has(h) && headers.indexOf(h) === i);
  return json.table.rows.map(row => {
    const obj = {}; headers.forEach((h,i)=>{ if(h && obj[h] === undefined) obj[h] = row.c[i]?.v ?? ''; });
    const title = obj['콘텐츠 이름']; const link = obj['콘텐츠 링크'];
    if (!title && !link) return null;
    return { channel:channel.key, channelLabel:channel.label, date:parseDate(obj['업로드 날짜']), title:title || '(제목 없음)', topic:obj['콘텐츠 주제'] || '미분류', owner:obj['담당자'] || '—', link:link || '', views:Number(obj[channel.metric]) || 0, raw:obj };
  }).filter(Boolean);
}

function isNumericColumn(name){ return /수$|전환$/.test(name); }
function cellValue(row, column){
  if(column === '채널') return row.channelLabel;
  if(column === '업로드 날짜') return displayDate(row.date);
  if(column === '콘텐츠 이름') return row.title;
  return row.raw?.[column] ?? '';
}
function renderCell(row, column){
  const value = cellValue(row,column);
  if(column === '콘텐츠 링크') return row.link ? `<a class="view-link" href="${escapeHtml(row.link.trim())}" target="_blank" rel="noopener">열기 ↗</a>` : '—';
  if(column === '콘텐츠 주제') return `<span class="topic-tag">${escapeHtml(value || '미분류')}</span>`;
  if(column === '콘텐츠 이름') return escapeHtml(value || '(제목 없음)');
  if(isNumericColumn(column)) return fmt.format(Number(value) || 0);
  return escapeHtml(value || '—');
}
function renderSummaryRow(rows, columns){
  return `<tr class="summary-row">${columns.map((column,index)=>{
    const numeric = isNumericColumn(column) || column === '조회수';
    let content = '—';
    if(numeric){
      const total = rows.reduce((sum,row)=>sum+(column==='조회수' ? row.views : Number(cellValue(row,column))||0),0);
      content = `<strong>${fmt.format(total)}</strong>`;
    } else if(column === '콘텐츠 이름') content = '<strong>기간 합계</strong>';
    else if(index === 0 && !columns.includes('콘텐츠 이름')) content = '<strong>기간 합계</strong>';
    else if(column === '채널') content = `<strong>${fmt.format(rows.length)}건</strong>`;
    return `<td class="${numeric?'number-cell':''}">${content}</td>`;
  }).join('')}</tr>`;
}

function filteredData(){
  const start = parseDate($('#startDate').value); const end = parseDate($('#endDate').value);
  return allData.filter(item => (!start || (item.date && item.date >= start)) && (!end || (item.date && item.date <= end)));
}
function render(){
  const scoped = filteredData();
  $('#kpiGrid').innerHTML = channels.map((ch,i)=>{
    const rows=scoped.filter(r=>r.channel===ch.key); const total=rows.reduce((s,r)=>s+r.views,0);
    return `<article class="kpi-card" style="--accent:${ch.accent}"><div class="kpi-top"><span class="channel">${ch.label}</span><span class="channel-index">0${i+1}</span></div><div class="metric"><strong>${fmt.format(total)}</strong><span>${ch.key==='x'?'노출':'조회'}</span></div><div class="kpi-foot">${fmt.format(rows.length)}개 콘텐츠</div><i class="accent-line"></i></article>`;
  }).join('');
  const rows = scoped.filter(r=>activeChannel==='all'||r.channel===activeChannel).sort((a,b)=>(b.date||0)-(a.date||0));
  $('#resultCount').textContent = `총 ${fmt.format(rows.length)}건`;
  const columns = activeChannel === 'all'
    ? ['채널','업로드 날짜','콘텐츠 이름','콘텐츠 주제','담당자','조회수','콘텐츠 링크']
    : (columnsByChannel[activeChannel] || ['담당자','업로드 날짜','콘텐츠 이름','콘텐츠 주제','콘텐츠 링크']);
  $('#contentHead').innerHTML = columns.map(c=>`<th class="${isNumericColumn(c)||c==='조회수'?'number-cell':''}">${c}</th>`).join('');
  const summaryRow = rows.length ? renderSummaryRow(rows,columns) : '';
  $('#contentRows').innerHTML = summaryRow + rows.map(r=>`<tr>${columns.map(c=>{
    const classes=[c==='업로드 날짜'?'date':'',c==='콘텐츠 이름'?'content-title':'',isNumericColumn(c)||c==='조회수'?'number-cell':''].filter(Boolean).join(' ');
    const content = c==='조회수' ? fmt.format(r.views) : renderCell(r,c);
    return `<td class="${classes}">${content}</td>`;
  }).join('')}</tr>`).join('');
  $('#emptyState').hidden = rows.length>0; $('table').hidden = rows.length===0;
  const start=$('#startDate').value, end=$('#endDate').value;
  $('#periodLabel').textContent = start||end ? `${start||'처음'} — ${end||'현재'}` : '전체 업로드 기간';
}
function renderTabs(){
  $('#tabs').innerHTML=[{key:'all',label:'전체'},...channels].map(c=>`<button class="tab ${c.key===activeChannel?'active':''}" data-channel="${c.key}" role="tab">${c.label}</button>`).join('');
  document.querySelectorAll('.tab').forEach(btn=>btn.onclick=()=>{activeChannel=btn.dataset.channel;renderTabs();render();});
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
init();

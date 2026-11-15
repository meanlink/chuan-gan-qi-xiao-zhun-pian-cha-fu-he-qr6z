import {platform} from '../api/entities.js';
import {heading} from '../components/common/shell.js';
import {esc,date,notify} from '../utils/dom.js';
import {submit} from '../hooks/forms.js';

const roleLabel={platform_admin:'平台管理员',admin:'业务负责人',analyst:'分析员',viewer:'观察员'};
const statusLabel={claimed:'已认领',conflict:'归属冲突',pending:'待认领'};

export async function platformPage(){
 const [labs,users,pending,conflicts]=await Promise.all([platform.labs(),platform.users(),platform.pending(),platform.conflicts()]);
 const labOptions=labs.map(l=>'<option value="'+l.id+'">'+esc(l.name)+'（'+esc(l.code)+'）</option>').join('');
 return heading('00 / PLATFORM','多实验室归属与旧数据认领','账号归属实验室后，接入、分析、批准、分发与下载全部按归属隔离；同一批次名可在不同实验室分别使用。旧数据认领前保持冻结。')
 +'<div class="platform-grid">'
 // 实验室管理
 +'<section class="panel"><div class="section-title"><h2>实验室</h2><span>'+labs.length+' 家</span></div>'
 +'<div class="lab-list">'+labs.map(l=>'<article class="lab-card"><strong>'+esc(l.name)+'</strong><small>编码 '+esc(l.code)+' · 建立于 '+date(l.created_at)+'</small></article>').join('')+'</div>'
 +'<form id="lab-form" class="stack-form"><label>实验室名称<input name="name" required minlength="2" placeholder="例如：衡准校准实验室"></label><label>实验室编码<input name="code" required minlength="2" placeholder="例如：HZ-LAB"></label><button class="primary" type="submit">新建实验室</button></form></section>'
 // 账号归属
 +'<section class="panel"><div class="section-title"><h2>账号归属</h2><span>'+users.length+' 个账号</span></div>'
 +'<div class="table-wrap"><table><thead><tr><th>账号</th><th>姓名</th><th>角色</th><th>归属实验室</th><th>调整归属</th></tr></thead><tbody>'
 +users.map(u=>'<tr><td>'+esc(u.email)+'</td><td>'+esc(u.name)+'</td><td>'+esc(roleLabel[u.role]||u.role)+'</td><td>'+esc(u.lab_name||'—（平台账号）')+'</td>'
 +'<td><select data-assign="'+u.id+'"><option value="">平台管理员（不归属实验室）</option>'+labs.map(l=>'<option value="'+l.id+'" '+(l.id===u.lab_id?'selected':'')+'>'+esc(l.name)+'</option>').join('')+'</select> <select data-role="'+u.id+'">'+Object.entries(roleLabel).map(([v,t])=>'<option value="'+v+'" '+(v===u.role?'selected':'')+'>'+esc(t)+'</option>').join('')+'</select></td></tr>').join('')
 +'</tbody></table></div>'
 +'<form id="user-form" class="stack-form"><div class="parameter-grid"><label>邮箱<input name="email" required type="email" placeholder="analyst@lab.local"></label><label>姓名<input name="name" required placeholder="账号姓名"></label></div>'
 +'<div class="parameter-grid"><label>角色<select name="role"><option value="analyst">分析员</option><option value="admin">业务负责人</option><option value="viewer">观察员</option><option value="platform_admin">平台管理员</option></select></label>'
 +'<label>归属实验室<select name="lab_id"><option value="">不归属（平台管理员）</option>'+labs.map(l=>'<option value="'+l.id+'">'+esc(l.name)+'</option>').join('')+'</select></label></div>'
 +'<label>初始密码<input name="password" required minlength="6" placeholder="至少 6 位"></label><button class="primary" type="submit">新建账号并设定归属</button></form></section>'
 // 待认领链
 +'<section class="panel"><div class="section-title"><h2>待认领旧数据链</h2><span>'+pending.length+' 条批次</span></div>'
 +(pending.length?pending.map(p=>'<article class="claim-card"><div><strong>'+esc(p.dataset_name)+'</strong><p>批次 #'+p.dataset_id+' · 分析 '+p.jobs+' 个 · 计划 '+p.reports+' 个 · 归档 '+p.deliveries+' 份</p><small>认领前已停止执行与分发；认领将整链划归同一实验室</small></div>'
 +'<div class="claim-actions"><select data-claim-lab="'+p.dataset_id+'">'+labOptions+'</select><button class="primary small" data-claim="'+p.dataset_id+'">整链认领</button></div>'
 +(p.claims.length?'<div class="claim-history">'+p.claims.map(c=>'<small class="claim-'+esc(c.status)+'">'+esc(statusLabel[c.status]||c.status)+(c.conflict_reason?'：'+esc(c.conflict_reason):'')+' · '+esc(c.actor)+' · '+date(c.updated_at)+'</small>').join('')+'</div>':'')
 +'</article>').join(''):'<p class="empty">没有待认领的旧数据链。</p>')+'</section>'
 // 冲突记录
 +'<section class="panel"><div class="section-title"><h2>归属冲突记录</h2><span>'+conflicts.length+' 条</span></div>'
 +(conflicts.length?'<div class="table-wrap"><table><thead><tr><th>批次</th><th>目标实验室</th><th>冲突原因</th><th>操作人</th><th>时间</th></tr></thead><tbody>'
 +conflicts.map(c=>'<tr><td>#'+c.dataset_id+'</td><td>'+(c.lab_id?('#'+c.lab_id):'—')+'</td><td>'+esc(c.conflict_reason)+'</td><td>'+esc(c.actor)+'</td><td>'+date(c.updated_at)+'</td></tr>').join('')
 +'</tbody></table></div>':'<p class="empty">尚无冲突。冲突会整次回滚并保留原归属。</p>')+'</section>'
 +'</div>';
}

export function bindPlatform(refresh){
 submit(document.querySelector('#lab-form'),async f=>{await platform.createLab({name:f.get('name'),code:f.get('code')});notify('实验室已建立');await refresh();});
 submit(document.querySelector('#user-form'),async f=>{
  const role=f.get('role');const labRaw=f.get('lab_id');
  await platform.createUser({email:f.get('email'),name:f.get('name'),role,password:f.get('password'),lab_id:role==='platform_admin'?null:(labRaw?Number(labRaw):null)});
  notify('账号已建立并设定归属');await refresh();
 });
 document.querySelectorAll('[data-assign]').forEach(sel=>{
  const id=sel.dataset.assign;
  sel.addEventListener('change',async()=>{
   const roleSel=document.querySelector('[data-role="'+id+'"]');
   const labRaw=sel.value;const role=roleSel.value;
   try{await platform.assignUser(id,{role,lab_id:role==='platform_admin'||!labRaw?null:Number(labRaw)});notify('归属已更新');await refresh();}catch(e){notify(e.message,true);}
  });
 });
 document.querySelectorAll('[data-role]').forEach(sel=>{
  const id=sel.dataset.role;
  sel.addEventListener('change',async()=>{
   const labSel=document.querySelector('[data-assign="'+id+'"]');
   const role=sel.value;const labRaw=labSel.value;
   try{await platform.assignUser(id,{role,lab_id:role==='platform_admin'||!labRaw?null:Number(labRaw)});notify('角色与归属已更新');await refresh();}catch(e){notify(e.message,true);}
  });
 });
 document.querySelectorAll('[data-claim]').forEach(btn=>btn.addEventListener('click',async()=>{
  const datasetId=Number(btn.dataset.claim);
  const labId=Number(document.querySelector('[data-claim-lab="'+datasetId+'"]').value);
  if(!confirm('确认把该批次连同其分析、分发计划与归档整体认领给所选实验室？'))return;
  try{await platform.claim({dataset_id:datasetId,lab_id:labId});notify('整链认领成功，分发计划已按原状态恢复');await refresh();}catch(e){notify(e.message,true);}
 }));
}

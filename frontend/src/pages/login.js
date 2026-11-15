import {api} from '../api/client.js';
import {session} from '../stores/session.js';
import {workspace} from '../stores/workspace.js';
import {esc} from '../utils/dom.js';
import {submit} from '../hooks/forms.js';
export function login(){
 const m=workspace.meta;
 document.querySelector('#app').innerHTML='<div class="login-scene"><section class="login-story"><div class="edition">MULTI-LAB FIELD NOTES</div><p class="eyebrow">'+esc(m.client)+'</p><h1>'+esc(m.name)+'</h1><p class="login-tag">多实验室共用系统 · 账号按实验室归属隔离</p><div class="flow-lines">'+m.entities.map((v,i)=>'<div><span>0'+(i+1)+'</span><strong>'+esc(v)+'</strong></div>').join('')+'</div><p class="login-foot">接入、分析、批准、分发与下载均按归属实验室隔离；越权编号直接拒绝。</p></section><section class="login-form"><p class="eyebrow">WORKSPACE ACCESS</p><h2>进入业务现场</h2><p>选择演示账号登录，继续当天的分析与复核。</p><form id="login"><label>演示账号<select name="email"><optgroup label="平台管理（不归属实验室）"><option value="platform@demo.local">宿岚 · 平台管理员</option></optgroup><optgroup label="望衡仪器校准实验室"><option value="admin@demo.local">林知 · 业务负责人</option><option value="analyst@demo.local">陈舟 · 分析员</option><option value="viewer@demo.local">周禾 · 观察员</option></optgroup><optgroup label="启衡计量校准实验室"><option value="qh-admin@demo.local">岑越 · 业务负责人</option><option value="qh-analyst@demo.local">沈砚 · 分析员</option><option value="qh-viewer@demo.local">闻笛 · 观察员</option></optgroup></select></label><label>密码<input name="password" type="password" value="Demo123!" required autocomplete="current-password"></label><button type="submit" class="primary">进入工作室 ↗</button></form><p class="hint">演示密码 Demo123! · 平台管理员管理实验室与旧数据认领，不参与业务操作</p></section></div>';
 submit(document.querySelector('#login'),async f=>{const data=await api('/auth/login',{method:'POST',body:JSON.stringify(Object.fromEntries(f))});session.save(data);location.hash=data.user.role==='platform_admin'?'#/platform':'#/overview';});
}

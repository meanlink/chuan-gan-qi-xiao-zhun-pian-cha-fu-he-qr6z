import {api} from './client.js';
export const datasets={list:()=>api('/datasets'),get:id=>api('/datasets/'+id),create:data=>api('/datasets',{method:'POST',body:JSON.stringify(data)})};
export const jobs={list:()=>api('/jobs'),get:id=>api('/jobs/'+id),create:data=>api('/jobs',{method:'POST',body:JSON.stringify(data)}),approve:id=>api('/jobs/'+id+'/approve',{method:'POST'})};
export const reports={list:()=>api('/reports'),create:data=>api('/reports',{method:'POST',body:JSON.stringify(data)}),toggle:id=>api('/reports/'+id+'/toggle',{method:'POST'}),deliveries:()=>api('/deliveries')};
export const platform={
 labs:()=>api('/platform/labs'),
 createLab:data=>api('/platform/labs',{method:'POST',body:JSON.stringify(data)}),
 users:()=>api('/platform/users'),
 createUser:data=>api('/platform/users',{method:'POST',body:JSON.stringify(data)}),
 assignUser:(id,data)=>api('/platform/users/'+id+'/assign',{method:'POST',body:JSON.stringify(data)}),
 pending:()=>api('/platform/claims/pending'),
 conflicts:()=>api('/platform/claims/conflicts'),
 claim:data=>api('/platform/claims',{method:'POST',body:JSON.stringify(data)}),
};

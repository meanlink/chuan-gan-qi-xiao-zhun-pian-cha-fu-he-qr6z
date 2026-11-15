/** @typedef {{id:number,name:string,source:string,rows:number,checksum:string,lab_id:number|null}} Dataset */
/** @typedef {{id:number,name:string,dataset_id:number,status:string,result:Object,approved:boolean,lab_id:number|null}} AnalysisJob */
/** @typedef {{id:number,name:string,job_id:number,destination:string,next_run:number,enabled:boolean,lab_id:number|null}} ReportSchedule */
/** @typedef {{id:number,email:string,name:string,role:string,lab_id:number|null,lab_name:string|null}} SessionUser */
/** @typedef {{id:number,name:string,code:string,created_at:number}} Lab */
/** @typedef {{id:number,dataset_id:number,lab_id:number|null,status:'pending'|'claimed'|'conflict',actor:string,detail:Object,conflict_reason:string,updated_at:number}} LabClaim */
export {};

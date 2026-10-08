// Deterministic geometry check, NOT a human-performance or accuracy study.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const source=fs.readFileSync(__dirname+'/web/app.js','utf8');
const start=source.indexOf('function excludedPath('),end=source.indexOf('\nfunction appliedCorners',start);
const context=vm.createContext({});vm.runInContext(source.slice(start,end),context);
const marks=[[.08,.08],[.5,.08],[.92,.08],[.08,.5],[.92,.5],[.08,.92],[.5,.92],[.92,.92]];
const cases=[
 {name:'full page',box:[0,0,1,1]},
 {name:'left edge lost',box:[.15,0,1,1]},
 {name:'right edge lost',box:[0,0,.85,1]},
 {name:'top edge lost',box:[0,.15,1,1]},
 {name:'bottom edge lost',box:[0,0,1,.85]},
 {name:'inner rectangle only',box:[.2,.2,.8,.8]}];
const results=cases.map(({name,box:[l,t,r,b]})=>{
 const polygon=[[l,t],[r,t],[r,b],[l,b]];
 const path=vm.runInContext('excludedPath('+JSON.stringify(polygon)+')',context);
 const numbers=path.split('Z M')[1].match(/[\d.]+/g).map(Number);
 const actual=numbers.reduce((out,v,i)=>{if(i%2===0)out.push([v/100,numbers[i+1]/100]);return out;},[]);
 assert.deepEqual(actual,polygon);
 const lost=marks.filter(([x,y])=>x<l||x>r||y<t||y>b).length;
 return {case:name,required_markers:marks.length,markers_excluded:lost,overlay_geometry_matches:true,automatic_only_retains:marks.length-lost,manual_full_frame_retains:8,manual_full_frame_is_scripted_oracle:true};
});
console.log(JSON.stringify({kind:'synthetic_geometry_development_check',cases:results,human_users:0,overlay_does_not_change_crop_pixels:true,human_error_reduction_measured:false,interpretation:'The overlay exposes removed geometry. A scripted full-frame correction retains known marks, with or without the overlay. No measured advantage over ordinary manual correction is claimed.'},null,2));

const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const root=path.resolve(__dirname,'..');
let checks=0;
const form={Map:class{
 constructor(name){this.name=name;this.sections=[];this.data={get:()=>undefined};}
 section(type,name){const s={name,options:[],option(type,name){const o={name,values:[],value(v){this.values.push(v);}};this.options.push(o);return o;}};this.sections.push(s);return s;}
 render(){return Promise.resolve(this);}
}};
function E(tag,attrs,children){return {tag,attrs,children};}
async function main(){
 const dir=path.join(root,'package/atech-gateway/files/www/luci-static/resources/view/gateway');
 for(const file of fs.readdirSync(dir)){
  const src=fs.readFileSync(path.join(dir,file),'utf8');new Function(src);checks++;
  const calls=[];const context={view:{extend:o=>o},form,E,_:s=>s,L:{url:s=>'/'+s},rpc:{declare:d=>{calls.push(d);return async()=>({site:'Bench',serial:'TEST',sim:'A',version:'dev',hardware_validated:false,up:false});}},poll:{add:()=>{}},dom:{content:(node,children)=>node.children=children},ui:{}};
  const view=vm.runInNewContext('(function(){'+src+'})()',context);
  if(file==='settings.js'){
   const node=await view.render();const maps=node.children;assert.equal(maps.length,2);
   const options=maps[1].sections[0].options;
   assert(options.find(o=>o.name==='pincode').password);
   assert(options.find(o=>o.name==='password').password);
   assert(options.find(o=>o.name==='auto'));checks+=4;
  }else if(file==='controllers.js'){
   const map=await view.render();const open=map.sections[0].options.find(o=>o.name==='open');
   map.data.get=(_,s,k)=>({address:'javascript:alert(1)',scheme:'http'})[k];assert.equal(open.cfgvalue('x'),'—');
   map.data.get=(_,s,k)=>({address:'192.168.50.101',scheme:'https'})[k];assert.equal(open.cfgvalue('x').attrs.href,'https://192.168.50.101');checks+=2;
  }else{
   const node=view.render(await view.load());assert(node.children.length>3);assert(calls.some(c=>c.method==='powercycle'));checks+=2;
  }
 }
 for(const file of ['usr/share/luci/menu.d/atech-gateway.json','usr/share/rpcd/acl.d/atech-gateway.json']){JSON.parse(fs.readFileSync(path.join(root,'package/atech-gateway/files',file)));checks++;}
 const acl=JSON.parse(fs.readFileSync(path.join(root,'package/atech-gateway/files/usr/share/rpcd/acl.d/atech-gateway.json')));
 assert(!acl.unauthenticated);assert(!acl['atech-gateway'].read.ubus['atech.gateway'].includes('powercycle'));checks+=2;
 console.log(`${checks} JavaScript/form/ACL checks passed. LuCI runtime and hardware not emulated.`);
}
main().catch(e=>{console.error(e);process.exit(1);});

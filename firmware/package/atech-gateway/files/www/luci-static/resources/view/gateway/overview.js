'use strict';
'require view';
'require rpc';
'require poll';
'require ui';
'require dom';
var status=rpc.declare({object:'atech.gateway',method:'status',expect:{}});
var cellular=rpc.declare({object:'network.interface.cellular',method:'status',expect:{}});
var restart=rpc.declare({object:'atech.gateway',method:'powercycle',expect:{}});
var selectSIM=rpc.declare({object:'atech.gateway',method:'select_sim',params:['slot'],expect:{}});
function card(icon,label,value,detail){return E('div',{class:'ag-card'},[E('span',{class:'ag-icon','aria-hidden':'true'},icon),E('small',{},label),E('strong',{},value),E('span',{},detail)]);}
return view.extend({
 handleSaveApply:null,handleSave:null,handleReset:null,
 load:function(){return Promise.all([status(),cellular().catch(function(){return {};})]);},
 render:function(data){
  var root=E('div');
  var action=function(fn){ui.showModal(_('Modem power cycle?'),[
   E('ul',{},[E('li',{},_('Cellular disconnection')),E('li',{},_('Modem power cut')),E('li',{},_('Validated hardware only'))]),
   E('div',{class:'right'},[E('button',{class:'btn',click:ui.hideModal},_('Cancel')),
    E('button',{class:'btn cbi-button-action',click:function(){ui.hideModal();return fn().then(function(r){ui.addNotification(null,E('p',{},r.message),r.ok?'info':'error');}).catch(function(e){ui.addNotification(null,E('p',{},_('Recovery request failed: ')+e.message),'error');});}},_('Continue'))])]);};
  var draw=function(d){var s=d[0],c=d[1];dom.content(root,[
   E('style',{},'.ag-brand{display:flex;align-items:center;justify-content:space-between;gap:24px;flex-wrap:wrap;margin:12px 0 24px}.ag-brand img{width:250px;max-width:100%;height:auto;background:#fff;border-radius:8px;padding:12px}.ag-brand h2{margin:0 0 6px}.ag-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin:20px 0}.ag-card{padding:22px;border:1px solid #d6e2ec;border-radius:10px;display:flex;flex-direction:column;gap:9px}.ag-card strong{font-size:24px}.ag-card small{color:#526b7b;font-size:13px}.ag-icon{color:#0078c7;font-size:28px}.ag-actions{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}.ag-actions .btn{padding:14px 20px;font-size:15px;min-height:48px}.ag-service{margin-top:28px}'),
   E('div',{class:'ag-brand'},[E('img',{src:L.resource('gateway/atlantis-logo.svg'),alt:'Atlantis Technologies'}),E('div',{},[E('h2',{},s.site||_('Dashboard')),E('span',{},s.serial+' · '+s.version)])]),
   E('div',{class:'ag-grid'},[
    card(c.up?'✓':'×',_('Cellular'),c.up?_('Connected'):_('Offline'),'LTE · QMI'),
    card('▥',_('Modem USB'),s.modem_present?_('Detected'):_('Not detected'),'EC25-AF Mini PCIe'),
    card('▣',_('SIM'),s.sim,s.esim_populated?_('A · SIM / B · eSIM'):_('Physical SIM · A')),
    card('⌁',_('Default setup IP'),'192.168.50.1',_('Wi-Fi / Ethernet'))]),
   E('div',{class:'ag-actions'},[
    E('a',{class:'btn cbi-button-action',href:L.url('admin/gateway/controllers')},_('▤ Controllers')),
    E('a',{class:'btn',href:L.url('admin/gateway/settings')},_('▥ Cellular')),
    E('a',{class:'btn',href:L.url('admin/network/wireless')},_('⌁ Wi-Fi')),
    E('a',{class:'btn',href:L.url('admin/network/network')},_('⇄ Ethernet'))]),
   E('h3',{class:'ag-service'},_('Service')),
   !s.hardware_validated?E('div',{class:'alert-message warning'},_('Carrier controls · Locked')):'',
   s.hardware_validated&&!s.powercut_validated?E('div',{class:'alert-message warning'},_('Modem recovery · Locked')):'',
   E('div',{class:'ag-actions'},[
    E('button',{class:'btn',disabled:!s.hardware_validated||!s.powercut_validated,click:function(){action(restart);}},_('Emergency modem power cycle')),
    E('button',{class:'btn',disabled:!s.hardware_validated||!s.powercut_validated||!s.esim_populated,click:function(){action(function(){return selectSIM(s.sim==='A'?'B':'A');});}},_('Switch SIM'))]),
   ]);};
  draw(data);poll.add(function(){return Promise.all([status(),cellular().catch(function(){return {};})]).then(draw);},10);return root;
 }
});

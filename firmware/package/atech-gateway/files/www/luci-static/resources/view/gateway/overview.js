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
function card(label,value,detail){return E('div',{class:'ag-card'},[E('small',{},label),E('strong',{},value),E('span',{},detail)]);}
return view.extend({
 handleSaveApply:null,handleSave:null,handleReset:null,
 load:function(){return Promise.all([status(),cellular().catch(function(){return {};})]);},
 render:function(data){
  var root=E('div');
  var action=function(fn){ui.showModal(_('Interrupt cellular traffic?'),[
   E('p',{},_('Emergency recovery cuts the modem supply and disconnects cellular users. Use only after validating the modem power-down procedure.')),
   E('div',{class:'right'},[E('button',{class:'btn',click:ui.hideModal},_('Cancel')),
    E('button',{class:'btn cbi-button-action',click:function(){ui.hideModal();return fn().then(function(r){ui.addNotification(null,E('p',{},r.message),r.ok?'info':'error');}).catch(function(e){ui.addNotification(null,E('p',{},_('Recovery request failed: ')+e.message),'error');});}},_('Continue'))])]);};
  var draw=function(d){var s=d[0],c=d[1];dom.content(root,[
   E('style',{},'.ag-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin:20px 0}.ag-card{padding:22px;border:1px solid #dde4e8;border-radius:10px;display:flex;flex-direction:column;gap:9px}.ag-card strong{font-size:24px}.ag-card small{color:#62717a}.ag-actions{display:flex;gap:12px;flex-wrap:wrap}'),
   E('h2',{},s.site||_('Walchem Gateway')),E('p',{},s.serial+' · '+s.version),
   E('div',{class:'ag-grid'},[
    card(_('Cellular'),c.up?_('Connected'):_('Disconnected'),_('QMI data session')),
    card(_('Modem USB'),s.modem_present?_('Detected'):_('Not detected'),'Quectel EC25-AF Mini PCIe'),
    card(_('Configured SIM'),s.sim,s.esim_populated?_('A: removable SIM; B: provisioned eSIM'):_('A: removable SIM; eSIM U20 not installed')),
    card(_('Default setup address'),'192.168.50.1',_('Wi-Fi or Ethernet'))]),
   !s.hardware_validated?E('p',{class:'alert-message warning'},_('Carrier control is locked until prototype hardware validation. Network configuration remains available.')):'',
   s.hardware_validated&&!s.powercut_validated?E('p',{class:'alert-message warning'},_('Emergency recovery is locked pending modem power-down and sequencing validation.')):'',
   E('div',{class:'ag-actions'},[
    E('a',{class:'btn cbi-button-action',href:L.url('admin/gateway/settings')},_('Configure cellular')),
    E('a',{class:'btn',href:L.url('admin/network/wireless')},_('Wi-Fi settings')),
    E('a',{class:'btn',href:L.url('admin/network/network')},_('Ethernet / LAN settings')),
    E('button',{class:'btn',disabled:!s.hardware_validated||!s.powercut_validated,click:function(){action(restart);}},_('Emergency modem power cycle')),
    E('button',{class:'btn',disabled:!s.hardware_validated||!s.powercut_validated||!s.esim_populated,click:function(){action(function(){return selectSIM(s.sim==='A'?'B':'A');});}},_('Switch SIM'))]),
   E('h3',{},_('Controller access')),E('p',{},_('Connect controllers by Ethernet or gateway Wi-Fi. Internet access does not automatically provide inbound remote access.')),
   E('a',{class:'btn',href:L.url('admin/gateway/controllers')},_('Manage controllers'))]);};
  draw(data);poll.add(function(){return Promise.all([status(),cellular().catch(function(){return {};})]).then(draw);},10);return root;
 }
});

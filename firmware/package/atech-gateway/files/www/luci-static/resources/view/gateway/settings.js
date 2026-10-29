'use strict';
'require view';
'require form';
return view.extend({
 render:function(){
  var m=new form.Map('gateway',_('Site & Cellular'),_('Save the site name and carrier connection settings.'));
  var s=m.section(form.NamedSection,'main','gateway');
  var o=s.option(form.Value,'site_name',_('Site name'));o.rmempty=false;o.datatype='maxlength(64)';
  var n=new form.Map('network',_('Quectel EC25-AF connection'),_('The modem keeps its Quectel firmware. Enter the SIM provider’s APN and enable cellular. MB00 uses the removable SIM.'));
  s=n.section(form.NamedSection,'cellular','interface');
  o=s.option(form.Flag,'auto',_('Enable cellular'));o.rmempty=false;
  o=s.option(form.Value,'apn',_('Carrier APN'));o.datatype='maxlength(100)';o.rmempty=true;
  o.validate=function(section,value){return value||s.formvalue(section,'auto')!=='1'?true:_('Enter the provider APN before enabling cellular.');};
  o=s.option(form.Value,'pincode',_('SIM PIN'));o.password=true;o.datatype='and(uinteger,minlength(4),maxlength(8))';o.rmempty=true;
  o=s.option(form.ListValue,'auth',_('Authentication'));['none','pap','chap','both'].forEach(function(v){o.value(v,v);});
  o=s.option(form.Value,'username',_('Carrier username'));o.rmempty=true;o.datatype='maxlength(100)';
  o=s.option(form.Value,'password',_('Carrier password'));o.password=true;o.rmempty=true;o.datatype='maxlength(100)';
  o=s.option(form.ListValue,'pdptype',_('IP family'));o.value('ipv4','IPv4');o.default='ipv4';
  return Promise.all([m.render(),n.render()]).then(function(nodes){return E('div',{},nodes);});
 }
});

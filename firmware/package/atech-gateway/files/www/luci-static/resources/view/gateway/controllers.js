'use strict';
'require view';
'require form';
return view.extend({
 render:function(){
  var m=new form.Map('gateway',_('Controllers'),_('Save local web addresses. These are bookmarks, not automatic discovery or remote-access tunnels. Reserve IPs under Network → DHCP and DNS.'));
  var s=m.section(form.GridSection,'controller',_('Controller directory'));s.addremove=true;s.anonymous=true;
  var o=s.option(form.Value,'name',_('Name'));o.rmempty=false;o.datatype='maxlength(64)';
  o=s.option(form.Value,'address',_('IPv4 address'));o.datatype='ip4addr("nomask")';o.rmempty=false;
  o=s.option(form.ListValue,'scheme',_('Web protocol'));o.value('http','HTTP');o.value('https','HTTPS');o.default='http';
  o=s.option(form.DummyValue,'open',_('Local web page'));
  o.cfgvalue=function(section){var ip=m.data.get('gateway',section,'address'),scheme=m.data.get('gateway',section,'scheme')||'http';if(!/^(?:\d{1,3}\.){3}\d{1,3}$/.test(ip||'')||ip.split('.').some(function(octet){return +octet>255;})||!['http','https'].includes(scheme))return '—';ip=ip.split('.').map(function(octet){return Number(octet);}).join('.');var href=scheme+'://'+ip,remote=m.data.get('gateway','remote','gateway_host');if(typeof window!=='undefined'&&window.location.hostname===remote&&m.data.get('gateway','remote','enabled')==='1'){var slot=['10.0.100.101','10.0.100.102','10.0.100.103','10.0.100.104'].indexOf(ip)+1;var target=m.data.get('gateway','remote','controller'+slot+'_host');if(!slot||scheme!=='http'||!/^([a-z0-9][a-z0-9-]*\.)+[a-z0-9-]+$/.test(target||''))return '—';href='https://'+target;}return E('a',{href:href,target:'_blank',rel:'noopener noreferrer'},_('Open controller'));};
  return m.render();
 }
});

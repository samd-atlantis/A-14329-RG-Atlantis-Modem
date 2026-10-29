'use strict';
'require view';
'require form';
return view.extend({
 render:function(){
  var m=new form.Map('gateway',_('Controllers'),_('Save local web addresses. These are bookmarks, not automatic discovery or remote-access tunnels. Reserve IPs under Network → DHCP and DNS.'));
  var s=m.section(form.GridSection,'controller',_('Controller directory'));s.addremove=true;s.anonymous=true;
  var o=s.option(form.Value,'name',_('Name'));o.rmempty=false;o.datatype='maxlength(64)';
  o=s.option(form.Value,'address',_('IPv4 address'));o.datatype='ip4addr';o.rmempty=false;
  o=s.option(form.ListValue,'scheme',_('Web protocol'));o.value('http','HTTP');o.value('https','HTTPS');o.default='http';
  o=s.option(form.DummyValue,'open',_('Local web page'));
  o.cfgvalue=function(section){var ip=m.data.get('gateway',section,'address'),scheme=m.data.get('gateway',section,'scheme')||'http';if(!/^(?:\d{1,3}\.){3}\d{1,3}$/.test(ip||'')||ip.split('.').some(function(octet){return +octet>255;})||!['http','https'].includes(scheme))return '—';return E('a',{href:scheme+'://'+ip,target:'_blank',rel:'noopener noreferrer'},_('Open controller'));};
  return m.render();
 }
});

#!/usr/bin/env python3

import os
import os.path
import multiprocessing
import time
import random
import xmlrpc.client
import ssl
import cairo
import grp
import sys
import lliurex.net
import traceback
import gi
import subprocess
gi.require_version('Gtk','3.0')
gi.require_version('PangoCairo','1.0')

from gi.repository import Gtk, Gdk, GObject, GLib, PangoCairo, Pango, GdkPixbuf

import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

import gettext
gettext.textdomain('llx-network-config')
_ = gettext.gettext

MARGIN=6

class NetworkConfig:
	
	def __init__(self):

		context=ssl._create_unverified_context()
		self.client=xmlrpc.client.ServerProxy("https://localhost:9779",allow_none=True,context=context)
		try:
			if self.client.get_variable("","VariablesManager","INTERFACE_REPLICATION")!=None:
				self.open_dialog(_("Network Configuration"),_("Network reconfiguration is only allowed on independent servers"),"dialog-information")
				#self.start_gui()
			else:
				self.start_gui()
		except Exception as e:
			print(e)
			pass
		
		
	#def init

	def quit(self,*args):
		#aborts exit if app is applying changes
		if self.spinner.props.active:
			return True
		Gtk.main_quit()

	def start_gui(self):
		self._set_css_info()
		self.window=Gtk.Window()
		self.window.set_title("Netconf")
		if os.path.exists("./rsrc/llx_network.png"):
			banner="./rsrc/llx_network.png"
		else:
			banner="/usr/share/llx-network-config/rsrc/llx_network.png"
		self.window.connect("delete-event",self.quit)
		
		pb=GdkPixbuf.Pixbuf.new_from_file(banner)
		img_banner=Gtk.Image.new_from_pixbuf(pb)
		img_banner.props.halign=Gtk.Align.CENTER
		img_banner.set_margin_left(MARGIN*2)
		img_banner.set_hexpand(True)
#		img_banner.set_vexpand(True)

		grid=Gtk.Grid()
		grid.set_hexpand(True)
		grid.set_vexpand(True)
		grid.set_margin_left(MARGIN)
		grid.set_margin_right(MARGIN)
		grid.set_margin_top(MARGIN)
		grid.set_margin_bottom(MARGIN)
		grid.set_row_spacing(MARGIN)
		grid.set_column_spacing(MARGIN)
		grid.set_name("WHITE_BACKGROUND")
		self.internal_speed_label=self._format_grid_label()
		grid.attach(img_banner,0,0,3,1)
		grid.attach(self.internal_speed_label,0,1,1,1)
		lbl_int_ip=self._format_grid_label(_("<sup>Internal IP</sup>"))
		grid.attach(lbl_int_ip,1,1,1,1)
		lbl_int_mask=self._format_grid_label(_("<sup>Internal mask</sup>"))
		grid.attach(lbl_int_mask,2,1,1,1)
		self.internal_combobox=Gtk.ComboBox()
		grid.attach(self.internal_combobox,0,2,1,1)
		self.internal_ip_entry=Gtk.Entry()
		grid.attach(self.internal_ip_entry,1,2,1,1)
		self.internal_mask_entry=Gtk.Entry()
		grid.attach(self.internal_mask_entry,2,2,1,1)

		self.external_speed_label=self._format_grid_label()
		grid.attach(self.external_speed_label,0,3,1,1)
		lbl_ext_conf=self._format_grid_label(_("<sup>External configuration mode</sup>"))
		lbl_ext_conf.set_halign(Gtk.Align.CENTER)
		grid.attach(lbl_ext_conf,1,3,2,1)

		self.external_combobox=Gtk.ComboBox()
		grid.attach(self.external_combobox,0,4,1,1)
		self.dhcp_radiobutton=Gtk.RadioButton().new_with_label(None,"DHCP")
		self.dhcp_radiobutton.set_halign(Gtk.Align.END)
		self.dhcp_radiobutton.connect("toggled",self.radio_button_changed)
		self.manual_radiobutton=Gtk.RadioButton.new_with_label_from_widget(self.dhcp_radiobutton,"Manual")
		grid.attach(self.dhcp_radiobutton,1,4,1,1)
		grid.attach(self.manual_radiobutton,2,4,1,1)

		self.rvl_box=Gtk.Revealer()
		rvl_grid=Gtk.Grid()
		rvl_grid.set_column_spacing(MARGIN)
		lbl_manual=self._format_grid_label(_("<sup>Manual options</sup>"))
		rvl_grid.attach(lbl_manual,0,0,1,1)
	
		lbl_ext_ip=self._format_grid_label(_("<sup>External IP</sup>"))
		rvl_grid.attach(lbl_ext_ip,0,1,1,1)
		lbl_ext_mask=self._format_grid_label(_("<sup>External mask</sup>"))
		rvl_grid.attach(lbl_ext_mask,1,1,1,1)
		lbl_ext_gw=self._format_grid_label(_("<sup>External gateway</sup>"))
		rvl_grid.attach(lbl_ext_gw,2,1,1,1)
		self.external_ip_entry=Gtk.Entry()
		rvl_grid.attach(self.external_ip_entry,0,2,1,1)
		self.external_mask_entry=Gtk.Entry()
		rvl_grid.attach(self.external_mask_entry,1,2,1,1)
		self.external_gateway_entry=Gtk.Entry()
		rvl_grid.attach(self.external_gateway_entry,2,2,1,1)
		self.rvl_box.add(rvl_grid)
		grid.attach(self.rvl_box,0,5,4,1)
	
		lbl_dns=self._format_grid_label(_("<sup>DNS</sup>"))
		grid.attach(lbl_dns,0,8,1,1)
		self.dns1_entry=Gtk.Entry()
		grid.attach(self.dns1_entry,0,9,1,1)
		self.dns2_entry=Gtk.Entry()
		grid.attach(self.dns2_entry,1,9,1,1)
#		apply_button=Gtk.Button().new_from_icon_name(Gtk.STOCK_APPLY,Gtk.IconSize.BUTTON)
		apply_button=Gtk.Button().new_from_stock(Gtk.STOCK_APPLY)
		apply_button.set_halign(Gtk.Align.END)
		apply_button.connect("clicked",self.apply_clicked)
		grid.attach(apply_button,2,9,1,1)

		self.spinner=Gtk.Spinner()
		grid.attach(self.spinner,1,1,1,8)
		self.window.add(grid)
		self.window.show_all()
		ret=self.set_default_gui_values()
		if ret[0]:
			Gtk.main()
		else:
			self.open_dialog(_("Network Configuration"),_("Error getting values.")+"\n[<b>"+str(ret[1])+"</b>]")
	#def start_gui

	def _format_grid_label(self,label_text=None):
		label=Gtk.Label()
		if label_text:
			label.set_markup("%s"%label_text)
		label.set_halign(Gtk.Align.START)
		label.set_name("ENTRY_LABEL")
		label.set_margin_bottom(0)
		return label
	#def _format_grid_label
	
	def set_default_gui_values(self):

		try:
			var=self.client.get_variables("","VariablesManager")
			internal=var["INTERNAL_INTERFACE"]["value"]
			external=var["EXTERNAL_INTERFACE"]["value"]
			dns1=var["DNS_EXTERNAL"]["value"][0]
			dns2=var["DNS_EXTERNAL"]["value"][1]
		
	
			self.iiface_model=Gtk.ListStore(str)
			self.eiface_model=Gtk.ListStore(str)
		
			self.internal_combobox.set_model(self.iiface_model)
			self.external_combobox.set_model(self.eiface_model)
			rendi=Gtk.CellRendererText()
			self.internal_combobox.pack_start(rendi,True)
			self.internal_combobox.add_attribute(rendi,"text",0)
			self.internal_combobox.connect("changed",self.get_link_speed,0)
			rende=Gtk.CellRendererText()
			self.external_combobox.pack_start(rende,True)
			self.external_combobox.add_attribute(rende,"text",0)
			self.external_combobox.connect("changed",self.get_link_speed,1)
			self.interfaces=lliurex.net.get_devices_info()		
		
			count=0
			i_id=0
			e_id=0
			for item in self.interfaces:
				if "eth" in item["name"]:
					self.iiface_model.append([item["name"]])
					if item["name"]==internal:
						i_id=count
					self.eiface_model.append([item["name"]])
					if item["name"]==external:
						e_id=count
				count+=1
			
			
				
			self.internal_combobox.set_active(i_id)
			if len(self.iiface_model)>1:
				self.external_combobox.set_active(e_id)
			else:
				self.external_combobox.set_active(0)
			
			if self.client.is_static("","NetworkManager",external)['result']:
				self.manual_radiobutton.set_active(True)

			ip=lliurex.net.get_ip(internal)
			mask=lliurex.net.get_netmask(internal)
		
			self.internal_ip_entry.set_text(ip)
			self.internal_mask_entry.set_text(mask)

			
			
			ip=lliurex.net.get_ip(external)
			self.external_mask_entry.set_text(lliurex.net.get_netmask(external))
			self.external_gateway_entry.set_text(lliurex.net.get_default_gateway()[1])
			ip=ip.split(".")
			self.external_ip_entry.set_text(".".join(ip))
		
			self.dns1_entry.set_text(dns1)
			self.dns2_entry.set_text(dns2)
		
		

			
			return [True,""]
				
		except Exception as e:

			top = traceback.extract_stack()[-1]
			f=top[0]
			line=str(top[1])
			txt="%s at line %s : %s"%(f,line,str(e))
			
			return [False,txt]
			
		
		
	#def set_default_gui_values
	
	def get_link_speed(self,widget,id):
		
		tree_iter = widget.get_active_iter()
		if tree_iter != None:
			model = widget.get_model()
			try:
				speed=lliurex.net.get_device_info(model[tree_iter][0])["Speed"][0]
			except:
				speed="Unknown speed"
			if id==0:
				self.internal_speed_label.set_markup(_("<sup>Internal interface %s</sup>")%speed)
			else:
				self.external_speed_label.set_markup(_("<sup>External interface %s</sup>")%speed)
				
		
	#def get_link_speed
	
	def is_static(self,eth):
		
		ret=False
		
		try:
		
			f=open("/etc/network/interfaces")
			lines=f.readlines()
			f.close()
			
			for line in lines:
				if eth in line:
					if "static" in line:
						ret=True
			
		except:
			
			pass
			
		return ret
		
	#def is_static

	
	def get_gui_values(self):
		
		var={}
		try:
			tmp=self.client.get_variables("","VariablesManager")
			var["srv_domain_name"]=tmp["INTERNAL_DOMAIN"]["value"]
			var["srv_name"]=tmp["HOSTNAME"]["value"]
			
			var["masterkey"]=self.get_n4d_key()
			var["remote_ip"]="localhost"
			
			iter=self.internal_combobox.get_active_iter()
			if iter!=None:
				var["internal_iface"]=self.iiface_model.get(iter,0)[0]
			else:
				var["internal_iface"]=None
			iter=self.external_combobox.get_active_iter()
			if iter!=None:
				var["external_iface"]=self.eiface_model.get(iter,0)[0]
			else:
				var["external_iface"]=None

			var["srv_ip"]=self.internal_ip_entry.get_text()
			var["internal_mask"]=self.internal_mask_entry.get_text()
			var["external_ip"]=self.external_ip_entry.get_text()
			var["external_mask"]=self.external_mask_entry.get_text()
			var["external_gateway"]=self.external_gateway_entry.get_text()
			var["dns1"]=self.dns1_entry.get_text()
			var["dns2"]=self.dns2_entry.get_text()
					
			
			if self.dhcp_radiobutton.get_active():
				var["external_mode"]="dhcp"
			else:
				var["external_mode"]="manual"
		
			return var
		
		except Exception as e:
			top = traceback.extract_stack()[-1]
			f=top[0]
			line=str(top[1])
			txt="%s at line %s : %s"%(f,line,str(e))
			return txt
		
	#def get_gui_values
	
	def test_values(self,var):
		
		if var["masterkey"]==None:
			return [False,_("You don't have root privileges to run this program")]
		
		if var["internal_iface"]==var["external_iface"]:
			return [False,_("Internal and external interfaces must be different")]
			
		lst=[]
		lst.append((_("Internal IP"),var["srv_ip"]))
		lst.append((_("Internal mask"),var["internal_mask"]))
		lst.append((_("External IP"),var["external_ip"]))
		lst.append((_("External mask"),var["external_mask"]))
		lst.append((_("Gateway"),var["external_gateway"]))
		lst.append((_("DNS #1"),var["dns1"]))
		lst.append((_("DNS #2"),var["dns1"]))
			
		for val in ( lst ):
			txt,item=val
			if not lliurex.net.is_valid_ip(item):
				return [False,_("'<b>%s</b>' must be a valid ip"%txt)]
				
		return [True,None]
		
	#def test_values

	
	def get_n4d_key(self):
		key=''	
		try:
			f=open("/etc/n4d/key","r")
			key=f.readline().strip("\n")
			f.close()
			return key
		except Exception as e:
			print(e)
			
	#def get_n4d_key


	def execute(self):

		msg="* Executing 015-network ... "
		sys.stdout.write(msg)
		exec(compile(open("/usr/share/zero-server-wizard/types/independent/actions/015-network.py").read(), "/usr/share/zero-server-wizard/types/independent/actions/015-network.py", 'exec'),locals())

		print("OK")
		msg="* Executing slapd open ports configuration ... "
		sys.stdout.write(msg)
		self.client.open_ports_slapd(self.template["masterkey"],"SlapdManager",self.template["srv_ip"])
		print("OK")
		msg="* Executing 050-dnsmasq ... "
		sys.stdout.write(msg)
		exec(compile(open("/usr/share/zero-server-wizard/types/independent/actions/050-dnsmasq.py").read(), "/usr/share/zero-server-wizard/types/independent/actions/050-dnsmasq.py", 'exec'),locals())
		print("OK")
		msg="* Executing 060-proxy ... "
		sys.stdout.write(msg)
		exec(compile(open("/usr/share/zero-server-wizard/types/independent/actions/060-proxy.py").read(), "/usr/share/zero-server-wizard/types/independent/actions/060-proxy.py", 'exec'),locals())
		print("OK")
		msg="* Restarting services ... "
		sys.stdout.write(msg)
		os.system("systemctl restart dnsmasq.service")		
		os.system("systemctl restart squid.service")		
		os.system("systemctl restart n4d.service")		
		print("OK")
		print("")
		print(" ** RECONFIGURATION FINISHED ** ")

	#def execute


	def apply_clicked(self,widget):
		
		var=self.get_gui_values()
		if type(var)!=type(dict()):
			self.open_dialog(_("Network Configuration"),_("Error getting values.")+"\n[<b>"+str(var)+"</b>]")
		ret=self.test_values(var)
		
		if ret[0]:
			self.spinner.show()
			self.spinner.start()
			self.window.set_sensitive(False)
			self.template=var
			self.process=multiprocessing.Process(target=self.execute)
			#t.daemon=True
			self.process.start()
			GLib.timeout_add(100,self.show_progress)
			
		else:

			self.open_dialog(_("Network Configuration"),ret[1])
		
		
	#def apply_clicked
	
	def show_progress(self):
		
		
#		self.progress_window.show()
#		self.progress_bar.pulse()
		
		if not self.process.is_alive():
			self.window.set_sensitive(True)
			self.spinner.stop()
			self.open_dialog(_("Network Configuration"),_("Configuration finished."),"dialog-information")
			
		return self.process.is_alive()
		
	#def show_progress

	def radio_button_changed(self,widget,force=False):
		
		if force:
			status=force
			
		else:
			status=not self.dhcp_radiobutton.get_active()	
		
		self.rvl_box.set_reveal_child(status)		
	#def radio_button_changed
	
	def window_close(self,widget):
		
		Gtk.main_quit()
		
	#def window_close
	
	def open_dialog(self,title,text,icon="emblem-important",show_cancel=False):

		label = Gtk.Label()
		label.set_markup(text)
		if show_cancel:
			dialog = Gtk.Dialog(title, None, Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT, (Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT,Gtk.STOCK_CANCEL,Gtk.ResponseType.CANCEL))
		else:
			dialog = Gtk.Dialog(title, None, Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT, (Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT))
		hbox = Gtk.HBox()
		img=Gtk.Image.new_from_icon_name(icon,Gtk.IconSize.DIALOG)
		hbox.pack_start(img,True,True,5)
		hbox.pack_start(label,True,True,10)
		hbox.show_all()
		dialog.vbox.pack_start(hbox,True,True,10)
		dialog.set_border_width(6)
		response = dialog.run()
		dialog.destroy()
		return response
		
	#def open_dialog
	
	def _set_css_info(self):
	
		css = b"""

		GtkEntry{
			font-family: Roboto;
			border:0px;
			border-bottom:1px grey solid;
			margin-top:0px;
			padding-top:0px;
		}

		GtkComboBox {
			border-bottom:1px grey solid;
		}
		GtkComboBox *{
			font-family: Roboto;
			border:0px;
			margin-top:0px;
			padding-top:0px;
		}

		GtkLabel {
			font-family: Roboto;
		}

		#ENTRY_LABEL{
			color:grey;
			padding:6px;
			padding-bottom:0px;
			margin-bottom:0px;
		}


		"""
		self.style_provider=Gtk.CssProvider()
		self.style_provider.load_from_data(css)
		Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),self.style_provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
	#def set_css_info	

	
#class NetworkConfig



if __name__=="__main__":
	
	nc=NetworkConfig()

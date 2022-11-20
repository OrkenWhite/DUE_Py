#!/usr/bin/python3
# -*- encoding: utf-8 -*-
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox
import tkinter.constants as tk_consts
import asyncio
import tkinter.simpledialog as simpledialog
import importlib.util

class ConnectData():
    def __init__(self):
        self.conn_name = tk.StringVar()
        self.username = tk.StringVar()
        self.port = tk.IntVar()
        self.port.set(6667)
        self.host = tk.StringVar()
        self.fullname = tk.StringVar()

class BotWindow:
    def __init__(self,controller):
        self.window = tk.Tk()
        self.window.geometry("1024x600")
        self.window.protocol("WM_DELETE_WINDOW",self.on_close)
        self.controller = controller
        self.window.title("Message collector bot")
        self.server_tabs = dict()
        self.connect_data = ConnectData()
        self.quitting = False
        self.init_controls()
        if importlib.util.find_spec('sv_ttk') is not None:
            import sv_ttk
            sv_ttk.set_theme("dark")
        controller.loop.create_task(self.updateLoop())
    def on_close(self):
        self.controller.close()
        self.quitting = True
    async def updateLoop(self):
        while not self.quitting:
            self.window.update()
            await asyncio.sleep(0)
        self.window.iconify()
        all_tasks = asyncio.all_tasks()
        await asyncio.gather(*all_tasks - {asyncio.current_task()})
        self.controller.close_future.set_result(True)
    def init_controls(self):
        self.tabview = ttk.Notebook(self.window)
        self.tabview.pack(expand=1,fill=tk_consts.BOTH,ipadx=3,ipady=3)
        self.connect_tab = ttk.Frame()
        self.tabview.add(self.connect_tab,text="Connect...")
        self.connect_tab.rowconfigure(0,weight=1)
        self.connect_tab.rowconfigure(1,weight=1)
        self.connect_tab.rowconfigure(2,weight=1)
        self.connect_tab.rowconfigure(3,weight=1)
        self.connect_tab.rowconfigure(4,weight=1)
        self.connect_tab.columnconfigure(0,weight=1)
        self.connect_tab.columnconfigure(1,weight=1)
        self.connect_tab.columnconfigure(2,weight=1)
        host_label = ttk.Label(self.connect_tab,text="Hostname:")
        host_entry = ttk.Entry(self.connect_tab,name="host_entry",textvariable=self.connect_data.host)
        host_label.grid(row=0,column=0,padx=5,pady=5,sticky=tk.W)
        host_entry.grid(row=0,column=1,columnspan=2,padx=5,pady=5,sticky=tk.EW)
        port_label = ttk.Label(self.connect_tab,text="Port:")
        port_entry = ttk.Entry(self.connect_tab,name="port_entry",textvariable=self.connect_data.port)
        port_label.grid(row=1,column=0,padx=5,pady=5,sticky=tk.W)
        port_entry.grid(row=1,column=1,columnspan=2,padx=5,pady=5,sticky=tk.EW)
        username_label = ttk.Label(self.connect_tab,text="Username:") 
        username_entry = ttk.Entry(self.connect_tab,name="username_entry",textvariable=self.connect_data.username)
        username_label.grid(row=2,column=0,padx=5,pady=5,sticky=tk.W)
        username_entry.grid(row=2,column=1,columnspan=2,padx=5,pady=5,sticky=tk.EW)
        fullname_label = ttk.Label(self.connect_tab,text="Full name:")
        fullname_entry = ttk.Entry(self.connect_tab,name="fullname_entry",textvariable=self.connect_data.fullname)
        fullname_label.grid(row=3,column=0,padx=5,pady=5,sticky=tk.W)
        fullname_entry.grid(row=3,column=1,columnspan=2,padx=5,pady=5,sticky=tk.EW)
        connect_button = ttk.Button(self.connect_tab,text="Connect",command=self.start_connect)
        connect_button.grid(row=4,column=0,columnspan=3,padx=5,pady=5,sticky=tk.EW)
    def create_server_tab(self,server_name):
        server_tab = ttk.Frame()
        server_tab.rowconfigure(0,weight=0)
        server_tab.rowconfigure(1,weight=0)
        server_tab.rowconfigure(2,weight=1)
        server_tab.rowconfigure(3,weight=1)
        server_tab.rowconfigure(4,weight=0)
        server_tab.rowconfigure(5,weight=0)
        server_tab.rowconfigure(6,weight=0)
        server_tab.columnconfigure(0,weight=1)
        server_tab.columnconfigure(1,weight=0)
        server_tab.columnconfigure(2,weight=0)
        server_tab.columnconfigure(3,weight=5)
        server_tab.columnconfigure(4,weight=0)
        disconnect_button = ttk.Button(server_tab,text="Disconnect",state="disabled",name="disconnect_button",command=lambda: self.quit_server(server_name))
        disconnect_button.grid(row=0,column=0,columnspan=5,padx=5,pady=5,sticky=tk.EW)
        channel_scroll = ttk.Scrollbar(server_tab,orient=tk_consts.VERTICAL)
        channel_label = ttk.Label(server_tab,text="Channels:")
        channel_label.grid(row=1,column=0,padx=5,pady=3,sticky=tk.NSEW)
        channel_list = ttk.Treeview(server_tab,yscrollcommand=channel_scroll.set,name="channel_list",selectmode="browse",show="tree")
        channel_scroll["command"] = channel_list.yview
        channel_scroll.grid(row=2,column=1,rowspan=3,padx=(0,5),pady=5,sticky=tk.NS)
        channel_list.bind("<<TreeviewSelect>>",lambda e: self.channel_selected(server_name))
        channel_list.grid(row=2,column=0,rowspan=3,padx=(5,0),pady=5,sticky=tk.NSEW)
        channel_add_button = ttk.Button(server_tab,text="+",state="disabled",name="channel_add_button",command=lambda: self.join_channel(server_name))
        channel_add_button.grid(row=2,column=2,padx=5,pady=5)
        channel_remove_button = ttk.Button(server_tab,name="remove_button",text="-",state="disabled",command=lambda: self.leave_channel(server_name,channel_list.selection()[0]))
        channel_remove_button.grid(row=3,column=2,padx=5,pady=5)
        messages_label = ttk.Label(server_tab,text="Messages:")
        messages_label.grid(row=1,column=3,padx=5,pady=3,sticky=tk.EW)
        messages = ttk.Treeview(server_tab,name="messages",columns=("date","sender","message"),show="headings",selectmode="browse")
        messages.column("date",stretch=False)
        messages.column("sender",stretch=False)
        messages.column("message",stretch=False,width=400)
        messages.heading("date",text="Date")
        messages.heading("sender",text="Sender")
        messages.heading("message",text="Message")
        messages.grid(row=2,column=3,rowspan=3,padx=(5,0),pady=(5,0),sticky=tk.NSEW)
        message_y_scroll = ttk.Scrollbar(server_tab,orient=tk_consts.VERTICAL,command=messages.yview)
        message_x_scroll = ttk.Scrollbar(server_tab,orient=tk_consts.HORIZONTAL,command=messages.xview)
        message_y_scroll.grid(row=2,column=4,rowspan=3,padx=0,pady=5,sticky=tk.NS)
        message_x_scroll.grid(row=5,column=3,padx=5,pady=(0,5),sticky=tk.EW)
        messages["xscrollcommand"] = message_x_scroll.set
        messages["yscrollcommand"] = message_y_scroll.set
        status_label = ttk.Label(server_tab,text="Connecting...",justify="right",name="status_label")
        status_label.grid(row=6,column=3,pady=5,sticky=tk.EW)
        self.tabview.add(server_tab,text=server_name)
        self.server_tabs[server_name] = server_tab
        self.tabview.select(server_tab)
    def start_connect(self):
        self.controller.loop.create_task(self.controller.connect(
            self.connect_data.host.get(),
            self.connect_data.port.get(),
            self.connect_data.username.get(),
            self.connect_data.fullname.get()))
    def join_channel(self,server):
        channel = simpledialog.askstring("Channel name","Which channel do you want to join?")
        if not channel == None:
            self.controller.join_channel(server,channel)
    def error_message(self,title,message):
        messagebox.showerror(title,message)
    def update_messages(self,server,channel):
        if len(self.server_tabs[server].nametowidget("channel_list").selection()) == 0:
            return
        if self.server_tabs[server].nametowidget("channel_list").selection()[0] == channel:
            messages = self.server_tabs[server].nametowidget("messages")
            for i in messages.get_children():
                messages.delete(i)
            for i in self.controller.messages[server][channel]:
                messages.insert("",tk.END,values=i)
    def channel_selected(self,server):
        channel = self.server_tabs[server].nametowidget("channel_list").selection()
        if len(channel) < 1:
            self.server_tabs[server].nametowidget("remove_button")["state"] = "disabled"
            return
        if channel[0] == "Private":
             self.server_tabs[server].nametowidget("remove_button")["state"] = "disabled"
        else:
             self.server_tabs[server].nametowidget("remove_button")["state"] = "normal"
        self.update_messages(server,channel[0])
    def add_channel(self,server,channel):
        self.server_tabs[server].nametowidget("channel_list").insert("",tk.END,text=channel,iid=channel)
    def successful_connection(self,host):
        self.server_tabs[host].nametowidget("disconnect_button")["state"] = "normal"
        self.server_tabs[host].nametowidget("channel_add_button")["state"] = "normal"
        self.server_tabs[host].nametowidget("status_label")["text"] = "Connected."
    def remove_server(self,server):
        self.tabview.forget(self.server_tabs[server])
        self.server_tabs.pop(server)
    def leave_channel(self,server,channel):
        self.controller.leave_channel(server,channel)
    def quit_server(self,server):
        self.controller.disconnect(server,"Message bot leaving")
    def remove_channel(self,server,channel):
        channel_list = self.server_tabs[server].nametowidget("channel_list")
        channel_list.delete(channel)
        channel_list.selection_set(channel_list.get_children()[0])


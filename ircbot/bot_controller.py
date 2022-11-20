#!/usr/bin/python3
#-*- encoding: utf-8 -*-
import bot_gui
import asyncio
import irc_client
import datetime

class MessageHandler:
    def __init__(self,name,controller):
        self.name = name
        self.controller = controller
    def handle_message(self,source,dest,msg):
        if dest == "*":
            return
        self.controller.add_message(self.name,dest if dest.startswith("#") else "Private",source.split('!')[0],msg)
    def error(self,msg):
        error_type = msg.split(' ')[0]
        match error_type:
            case 'Invalidnick':
                self.controller.wrong_nick(self.name)
            case 'Cantjoin':
                self.controller.cannot_join(self.name,msg.split(' ')[1])
            case 'Banned':
                self.controller.banned(self.name)
            case 'Needsreg':
                self.controller.need_registration(self.name)
    def server_message(self,header,msg):
        match header.split(' ')[0]:
            case 'Channel':
                if msg.split(' ')[0] == 'Joined':
                    self.controller.joined_channel(self.name,header.split(' ')[1],msg.split(' ')[1])
                elif msg.split(' ')[0] == 'Left':
                    self.controller.left_channel(self.name,header.split(' ')[1],msg.split(' ')[1])
    def kicked(self,source,channel,reason):
        self.controller.kicked(self.name,source,channel,reason)

class Controller:
    def __init__(self,loop,close_future):
        self.connected_servers = {}
        self.messages = {}
        self.loop = loop
        self.close_future = close_future
        self.gui = bot_gui.BotWindow(self)
    async def connect(self,hostname,port,username,fullname):
        available_future = self.loop.create_future()
        closing_future = self.loop.create_future()
        if hostname in self.messages:
            self.gui.error_message("Notice","We're already connected to this server!")
            return
        self.messages[hostname] = {}
        self.messages[hostname]["Private"] = list()
        self.gui.create_server_tab(hostname)
        try:
            self.connected_servers[hostname] = await asyncio.wait_for(self.loop.create_connection(lambda: irc_client.IRCProtocol(username,fullname,MessageHandler(hostname,self),available_future,closing_future),hostname,port),timeout=10)
            try:
                await asyncio.wait_for(available_future,timeout=10)
                self.connection_success(hostname)
                await closing_future
            except Exception as ex:
                self.gui.error_message("Error","Something bad happened in the connection to: " + hostname)
            finally:
                self.connected_servers[hostname][0].close()
                self.connected_servers.pop(hostname)
                self.messages.pop(hostname)
        except TimeoutError:
            self.gui.error_message("Connection error","Timed out to server: " + hostname)
        except:
             self.gui.error_message("Error","Something bad happened during connection to: " + hostname)
        finally:
             self.gui.remove_server(hostname)
    def connection_success(self,name):
        self.gui.add_channel(name,"Private")
        self.gui.successful_connection(name)
    def joined_channel(self,server,channel,user):
        if user.split('!')[0] == self.connected_servers[server][1].username:
            self.gui.add_channel(server,channel) 
            self.messages[server][channel] = list()
    def left_channel(self,server,channel,user):
        if user.split('!')[0] == self.connected_servers[server][1].username:
            self.remove_channel(server,channel)
    def remove_channel(self,server,channel):
        self.gui.remove_channel(server,channel)
        self.messages[server].pop(channel)
    def join_channel(self,server,channel):
        asyncio.create_task(self.connected_servers[server][1].join_channel(channel))
    def leave_channel(self,server,channel,reason="Message bot leaving"):
        asyncio.create_task(self.connected_servers[server][1].leave_channel(channel,reason))
    def disconnect(self,server,reason):
        asyncio.create_task(self.connected_servers[server][1].quit_server(reason))
    def add_message(self,server,channel,user,msg):
        if not channel == "Private" and not self.connected_servers[server][1].username in msg.split(' '):
            return
        self.messages[server][channel].append((datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),user,msg))
        self.gui.update_messages(server,channel)
    def kicked(self,server,user,channel,reason):
        self.gui.error_message("Kicked",f"We've been kicked from {channel} by {user}, reason {reason}")
        self.remove_channel(server,channel)
    def wrong_nick(self,server):
        self.gui.error_message("Wrong nick","This nickname connot be used.")
        self.connected_servers[server][1].quit_server("")
    def banned(self,server):
        self.gui.error_message("Banned","We are banned from this server: " + server)
    def need_registration(self,server):
        self.gui.error_message("Registration","This server needs registraion(not implemented): " + server)
        asyncio.create_task(self.connected_servers[server][1].quit_server(""))
    def cannot_join(self,server,channel):
        self.gui.error_message("Channel",f"Cannot join channel: {channel}")
    def close(self):
        for s in self.connected_servers:
            asyncio.create_task(self.connected_servers[s][1].quit_server(""))

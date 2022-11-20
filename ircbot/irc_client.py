#!/usr/bin/python3
# -*- coding: utf-8 -*-

import asyncio
import datetime

class IRCProtocol(asyncio.Protocol) :
    def __init__(self,username,fullname,msg_handler,available_future,loop_ender,client_name="owbot",blocksize=512):
        self.blocksize = blocksize
        self.username = username
        self.fullname = fullname
        self.blocksize = blocksize
        self.loop_ender = loop_ender
        self.available_future = available_future
        self.msg_handler = msg_handler
        self.client_name = client_name
    def connection_made(self,transport):
        self.is_connected = True
        self.transport = transport
        self.transport.write(f'USER {self.username} 0 * :{self.fullname}\r\n'.encode())
        self.transport.write(f'NICK {self.username}\r\n'.encode())
    def send_command(self,cmd):
        if not cmd.endswith("\r\n"):
            cmd += "\r\n"
        cmdargs = cmd.split(' ')
        cmdargs[0] = cmdargs[0].upper()
        cmd = ' '.join(cmdargs)
        self.transport.write(cmd.encode())
    async def send_message(self,recipient,message):
        self.transport.write(f'PRIVMSG {recipient} :{message}\r\n'.encode())
    def connection_lost(self,exc):
        self.loop_ender.set_result(True)
    def data_received(self,data):
        commands = data.decode().split("\r\n")
        self.handle_commands(commands)
    async def join_channel(self,channel):
        self.transport.write(f'JOIN {channel}\r\n'.encode())
    async def set_invisible(self,isInvisible):
        self.transport.write(f'MODE {self.username} {"+" if isInvisible else "-"}i')
    async def leave_channel(self,channel,reason):
        self.transport.write(f'PART {channel} :{reason}\r\n'.encode())
    async def quit_server(self,reason):
        self.transport.write(f'QUIT :{reason}\r\n'.encode())
    def handle_ctcp(self,source,command,args,doNotReply):
        source_username = source.split('!')[0]
        match command:
            case 'VERSION':
                if doNotReply:
                    self.msg_handler.server_message(f"CTCP {source_username}","Version {args}")
                else:
                    self.send_command(f"NOTICE {source_username} :\x01VERSION {self.client_name}\x01")
            case 'TIME':
                if doNotReply:
                    self.msg_handler.server_message(f"CTCP {source_username}","Time {args}")
                else:
                    localtime = datetime.datetime.now().strftime("%Y.%m.%d. %H:%M:%S")
                    self.send_command(f"NOTICE {source_username} :\x01TIME {localtime}\x01")
            case 'PING':
                if doNotReply:
                    now = datetime.datetime.now().timestamp()
                    elapsed = (now - float(args)) * 1000
                    self.msg_handler.server_message(f"CTCP {source_username}", f"Ping {elapsed} ms")
                else:
                    self.send_command(f"NOTICE {source_username} :\x01PING {args}\x01")
    def num_reply(self,command,args):
        match command:
            # We're ready to join
            case 1:
                 self.available_future.set_result(True)
            # Someone is away
            case 301:
                self.msg_handler.server_message("Away",f"Away {args[0]} {' '.join(args[1])[1:]}")
            # We are away
            case 305:
                self.msg_handler.server_message("Away",f"{' '.join(args)[1:]}")
            #We aren't away anymore
            case 306: 
                self.msg_handler.server_message("Away",f"{' '.join(args)[1:]}")
            # Is online?
            case 303:
                self.msg_handler.server_message("Online",f"{' '.join(args)[1:]}")
            # No channel topic
            case 331:
                self.msg_handler.server_message(f"Channel {args[0]}","Notopic")
            # Channel topic
            case 332:
                self.msg_handler.server_message(f"Channel {args[0]}",f"Topic {' '.join(args[1:])[1:]}")
            case 375:
                self.msg_handler.server_message("Motd","Begin")
            case 372:
                self.msg_handler.server_message("Motd",f"{' '.join(args)[1:]}")
            case 376:
                self.msg_handler.server_message("Motd","End")
            # Server time
            case 393:
                self.msg_handler.server_message(f"Time",f"{' '.join(args[1:])[1:]}")
            # No such user
            case 401:
                self.msg_handler.error(f"Nouser {args[0]}")
            # No such channel
            case 403:
                self.msg_handler.error(f"Nochannel {args[0]}")
            # Can't send message
            case 404:
                self.msg_handler.error(f"Cantsend {args[0]}")
            # Invalid nickname
            case 432:
                self.msg_handler.error(f"Invalidnick")
            # Used nickname
            case 433:
                self.msg_handler.error(f"Invalidnick")
            # Not registered
            case 451:
                self.msg_handler.error(f"Needsreg")
            # Wrong password
            case 464:
                self.msg_handler.error(f"Wrongpassword")
            # Banned from server
            case 465:
                self.msg_handler.error(f"Banned")
            # Going to be banned soon
            case 466:
                self.msg_handler.server_message("Ban","Bannedsoon")
            # Banned from channel, invite-only channel, key-only channel
            case 473 | 474 | 475:
                self.msg_handler.error(f"Cantjoin {args[0]} {' '.join(args[1:])[1:]}")
            # Channel full
            case 471:
                self.msg_handler.error(f"Cantjoin {args[0]}")
            # Connection restricted
            case 484:
                self.msg_handler.server_message(f"Connection","Connrestricted")
    def handle_message(self,source,destination,msg,doNotReply):
        if msg.startswith('\x01') and msg.endswith('\x01') and destination.split('!')[0] == self.username:
            stripped = msg.strip('\x01')
            self.handle_ctcp(source,stripped.split(' ')[0],' '.join(stripped.split(' ')[1:]),doNotReply)
        else:
            self.msg_handler.handle_message(source,destination,msg)
    def handle_kick(self,source,channel,args):
        if(args.split(' ')[0] == self.username):
            self.msg_handler.kicked(source,channel,' '.join(args.split(' ')[1:]))
        else:
            self.msg_handler.server_message(f"Channel {channel}","Kicked {source_user} {args}")
    def handle_commands(self,commands):
        for cmd in commands:
            cmdargs = cmd.split(' ')
            if len(cmdargs) < 2:
                continue
            if cmdargs[0] == "PING":
                self.send_command(' '.join(['PONG'] + cmdargs[1:]))
                continue
            source_user = cmdargs[0][1:]
            destination = cmdargs[2].replace(':','',1)
            args = ' '.join(cmdargs[3:]).replace(':','',1)
            match cmdargs[1]:
                case 'NOTICE':
                    self.handle_message(source_user,destination,args,True)
                case 'PRIVMSG':
                    self.handle_message(source_user,destination,args,False)
                case 'JOIN':
                    self.msg_handler.server_message(f"Channel {destination}",f"Joined {source_user}")
                case 'PART':
                    self.msg_handler.server_message(f"Channel {destination}",f"Left {source_user} {args}")
                case 'QUIT':
                    self.msg_handler.server_message(f"Quit",f"Left {source_user} {args}")
                case 'MODE':
                    self.msg_handler.server_message(f"Channel {destination}",f"Mode {source_user} {args}")
                case 'KICK':
                    self.handle_kick(source_user,destination,args)
                case 'TOPIC':
                    self.msg_handler.server_message(f"Channel {destination}",f"Topicset {source_user} {args}")
                case _:
                    if(cmdargs[1].isnumeric()):
                        self.num_reply(int(cmdargs[1]),cmdargs[3:])

    

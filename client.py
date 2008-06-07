#! /usr/bin/python
# coding=utf-8

#############################################################################
#                                                                           #
#   File: client.py                                                         #
#                                                                           #
#   Copyright (C) 2008 Du XiaoGang <dugang@188.com>                         #
#                                                                           #
#   This program is free software; you can redistribute it and/or modify    #
#   it under the terms of the GNU General Public License as published by    #
#   the Free Software Foundation; either version 2 of the License, or       #
#   (at your option) any later version.                                     #
#                                                                           #
#   Home: http://natvpn.googlecode.com                                      #
#   Blog: http://inside2004.cublog.cn                                       #
#                                                                           #
#############################################################################
from address import getMappedAddr
from messager import *
import threading
import socket
import time
import re
import os

# global flag
stopKeepMap = False
def keepMappedPort(srcPort, interval=5):
    global stopKeepMap
    if stopKeepMap:
        return
    # send data anywhere
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', srcPort))
    sock.sendto('hello', ('202.119.230.80', 12345))
    sock.close()
    # set timer
    t = threading.Timer(interval, keepMappedPort, [srcPort, interval])
    t.start()


def tryConnect(destIP, destPort, destPortRange, srcPort, sessID):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # use while/try to avoid srcPort confliction
    while True:
        try:
            sock.bind(('', srcPort))
            break
        except socket.error:
            # AddrInUse
            time.sleep(1)
            continue

    # send sessID to possible Port
    for i in range(-10, destPortRange):
        if destPort + i > 0:
            sock.sendto(sessID, (destIP, destPort + i))

    # wait reply
    sock.settimeout(10)
    while True:
        # read client data
        try:
            ret = sock.recvfrom(1024)
            if ret[0] == sessID:
                sock.close()
                return ret[1][1]
        except socket.timeout:
            # timeout
            sock.close()
            return -1


def updateClientConf(confFile, remote, lport):
    newContent = ''

    fp = open(confFile, 'r')
    while True:
        line = fp.readline()
        if line == '':
            break
        # process line
        if re.match('^[ \t]*port[ \t]+', line) != None:
            # port number
            newContent += ';' + line
            continue
        if re.match('^[ \t]*lport[ \t]+', line) != None:
            # lport number
            newContent += ';' + line
            continue
        if re.match('^[ \t]*rport[ \t]+', line) != None:
            # rport
            newContent += ';' + line
            continue
        if re.match('^[ \t]*nobind[ \t]+', line) != None:
            # nobind
            newContent += ';' + line
            continue
        if re.match('^[ \t]*remote[ \t]+', line) != None:
            # remote
            newContent += ';' + line
            continue
        # config line
        newContent += line
    fp.close()

    # new data
    newContent += 'remote ' + remote + '\n'
    newContent += 'lport ' + lport + '\n'

    # rewrite
    fp = open(confFile, 'w')
    fp.write(newContent)
    fp.close()


def natConnect(messager, mesgCheckInterval, stunServerList, OpenVPNConfFile, 
               srcPort=12345):
    global stopKeepMap

    sessID = int(time.time())

    # get my external addr
    myAddr = getMappedAddr(stunServerList, srcPort)
    if myAddr == '':
        print 'Failed to get our External Address.'
        return False
    elif myAddr == 'AddrInUse':
        print 'Local port(%d) is in used.' % srcPort
        return False
    print 'Our External Address: (%s).' % myAddr
    # start new thread to keep port mapping
    keepMappedPort(srcPort)

    # send client's 'HELLO'
    messager.send('HELLO/%u/%s' % (sessID, myAddr))
    print 'HELLO sent.'

    # wait for server's response
    while True:
        ms = messager.recv()
        for m in ms:
            m = m.strip(' \t\r\n')
            cols = m.split('/')
            # for 'BUSY/SESSID'
            if len(cols) == 2 and cols[0] == 'BUSY' \
               and cols[1] == '%u' % sessID:
                # OpenVPN is already running
                print 'Server is busying now, send RESET first.'
                stopKeepMap = True
                return False
            # for 'DONE/SESSID/PORT/IP'
            if len(cols) != 4:
                # invalid message
                continue
            if cols[0] != 'DONE':
                continue
            # check sessID
            if cols[1] != '%u' % sessID:
                continue
            print 'DONE received'
            # get client information
            serverIP = cols[2]
            serverPort = int(cols[3])
            # try connect
            stopKeepMap = True
            destPort = tryConnect(serverIP, serverPort, 30, srcPort, 
                                  '%u' % sessID)
            if destPort > 0:
                updateClientConf(OpenVPNConfFile,
                                 '%s %d' % (serverIP, destPort), 
                                 '%d' % srcPort)
                print 'Now VPN Server is listening on (%s:%d).' % (serverIP, destPort)
                print 'Please launch OpenVPN\'s client as soon as possible.'
                return True
            else:
                print 'Failed to connect VPN server.'
                return False
        # sleep
        time.sleep(mesgCheckInterval)


if __name__ == '__main__':
    ## for GMailMessager
    ## 给客户端所用的GMail帐号/密码
    #clientMail = 'openvpn.nat.user@gmail.com'
    #clientPasswd = '***'
    ## 给服务端所用的GMail帐号
    #serverMail = 'openvpn.nat.server@gmail.com'
    #messager = GMailMessager(clientMail, clientPasswd, serverMail)
    #mesgCheckInterval = 10

    # for GAppMessager
    messager = GAppMessager('client', '***', 'server')
    mesgCheckInterval = 1

    # 可用的STUN服务器列表
    stunServerList = ['stun1.l.google.com:19302', 'stun2.l.google.com:19302', 
                      'stun3.l.google.com:19302', 'stun4.l.google.com:19302']

    # 你的OpenVPN客户端配置文件路径
    OpenVPNConfFile = '/usr/local/etc/openvpn/client.ovpn'

    try:
        if natConnect(messager, mesgCheckInterval, stunServerList, 
                      OpenVPNConfFile) == True:
            os.spawnl(os.P_WAIT, '/usr/local/sbin/openvpn', 'openvpn', 
                      '--config', OpenVPNConfFile)
    except BaseException, e:
        print 'Catch Exception:', e
    time.sleep(3600)

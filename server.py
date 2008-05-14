#! /usr/bin/python

#############################################################################
#                                                                           #
#   File: server.py                                                         #
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
from messager import GMailMessager
import threading
import socket
import time
import os

def punch(destIP, destPort, srcPort):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(('', srcPort))
    except socket.error:
        # srcPort is in used
        sock.close()
        return 'AddrInUse'
    sock.sendto('hello', (destIP, destPort))
    sock.close()
    return ''


# global flag
stopKeepPunch = True
def keepPunch(destIP, destPort, srcPort, interval=5):
    global stopKeepPunch
    if stopKeepPunch:
        return
    # punch
    if punch(destIP, destPort, srcPort) == 'AddrInUse':
        return
    # set timer
    t = threading.Timer(interval, keepPunch, 
                        [destIP, destPort, srcPort, interval])
    t.start()


def acceptConnection(listenPort, waitTime, sessID):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # use while/try to avoid listenPort confliction (with keepPunch)
    while True:
        try:
            sock.bind(('', listenPort))
            break
        except socket.error:
            # AddrInUse
            time.sleep(1)
            continue

    timeLimit = int(time.time()) + waitTime
    while int(time.time()) < timeLimit:
        sock.settimeout(timeLimit - int(time.time()))
        # read client data
        try:
            ret = sock.recvfrom(1024)
            if ret[0] == sessID:
                sock.sendto(sessID, ret[1])
                sock.close()
                return True
        except socket.timeout:
            # timeout
            sock.close()
            return False
    sock.close()
    return False


def natListen(serverMail, serverPasswd, clientMail, mailCheckInterval, 
              stunServerList, OpenVPNPath, OpenVPNConfFile, srcPort=1194):
    global stopKeepPunch

    server = GMailMessager(serverMail, serverPasswd, clientMail)

    while True:
        try:
            # wait for client's request
            ms = server.recv()
            for m in ms:
                m = m.strip(' \t\r\n')
                cols = m.split('/')

                # for 'RESET/SESSID'
                if len(cols) == 2 and cols[0] == 'RESET':
                    # log
                    print time.ctime() + ' --> RESET received.'
                    # do
                    os.system('killall openvpn')
                    time.sleep(1)
                    os.system('killall -KILL openvpn')
                    # send server's 'DONE'
                    server.send('DONE/%s' % cols[1])
                    continue

                # for 'HELLO/SESSID/IP/PORT'
                if len(cols) != 4:
                    # invalid message
                    continue
                if cols[0] != 'HELLO':
                    continue
                # get client's information
                sessID = cols[1]
                clientIP = cols[2]
                clientPort = int(cols[3])
                # log
                print time.ctime() + ' --> HELLO received from (%s:%d).' % \
                      (clientIP, clientPort)

                # punch to client
                if punch(clientIP, clientPort, srcPort) == 'AddrInUse':
                    # send server's 'BUSY'
                    server.send('BUSY/%s' % sessID)
                    continue

                # get our udp addr/port
                myAddr = getMappedAddr(stunServerList, srcPort)
                if myAddr == '':
                    # stun server error, log
                    print time.ctime() + ' --> STUN server error.'
                    continue

                stopKeepPunch = False
                # start new thread to keep port mapping
                keepPunch(clientIP, clientPort, srcPort)

                # send server's 'DONE'
                server.send('DONE/%s/%s' % (sessID, myAddr))
                # wait for client's udp packet
                stopKeepPunch = True
                if acceptConnection(srcPort, 180, sessID):
                    # connection is established, log
                    print time.ctime() + ' --> OpenVPN is running.'
                    os.spawnl(os.P_NOWAIT, 
                              OpenVPNPath, 'openvpn', '--config', 
                              OpenVPNConfFile, '--lport', '%d' % srcPort)
                else:
                    # failed, log
                    print time.ctime() + \
                          ' --> Failed to accept new connection from (%s:%d).' % \
                          (clientIP, clientPort)
            # sleep
            time.sleep(mailCheckInterval)
        except KeyboardInterrupt:
            print time.ctime() + ' --> KeyboardInterrupt'
            break
        except BaseException, e:
            print time.ctime() + ' --> Catch Exception:', e
            stopKeepPunch = True
            continue


if __name__ == '__main__':
    # 给服务端所用的GMail帐号/密码,如实填写:)
    serverMail = 'openvpn.nat.server@gmail.com'
    serverPasswd = '********'
    # 给客户端所用的GMail帐号
    clientMail = 'openvpn.nat.user@gmail.com'
    # 服务端每次察新邮件的时间间隔,默认3分种,已经比较小了,不要修改
    # 参考 http://mail.google.com/support/bin/answer.py?answer=14257
    mailCheckInterval = 180
    # 可用的STUN服务器列表
    stunServerList = ['stun01.sipphone.com', 'stun.ekiga.net', 
                      'stun.fwdnet.net']
    # 你安装的OpenVPN执行文件路径
    OpenVPNPath = '/usr/local/sbin/openvpn'
    # 你的OpenVPN配置文件路径
    OpenVPNConfFile = '/usr/local/etc/server.conf'

    natListen(serverMail, serverPasswd, clientMail, mailCheckInterval, 
              stunServerList, OpenVPNPath, OpenVPNConfFile)

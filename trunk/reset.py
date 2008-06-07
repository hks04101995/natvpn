#! /usr/bin/python

#############################################################################
#                                                                           #
#   File: reset.py                                                          #
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
from messager import *
import time

def resetServer(messager, mesgCheckInterval):
    sessID = int(time.time())
    # send client's 'RESET'
    messager.send('RESET/%u' % sessID)
    print 'RESET sent.'
    # wait for server's reply
    while True:
        ms = messager.recv()
        for m in ms:
            m = m.strip(' \t\r\n')
            cols = m.split('/')
            # for 'RESET/SESSID'
            if len(cols) != 2:
                # invalid message
                continue
            if cols[0] != 'DONE' or cols[1] != '%u' % sessID:
                continue
            print 'Reset Successful.'
            return True
        # sleep
        time.sleep(mesgCheckInterval)


if __name__ == '__main__':
    ## for GMailMessager
    #clientMail = 'openvpn.nat.user@gmail.com'
    #clientPasswd = '***'
    #serverMail = 'openvpn.nat.server@gmail.com'
    #messager = GMailMessager(clientMail, clientPasswd, serverMail)
    #mesgCheckInterval = 10

    # for GAppMessager
    messager = GAppMessager('client', '***', 'server')
    mesgCheckInterval = 1

    resetServer(messager, mesgCheckInterval)

    time.sleep(3600)

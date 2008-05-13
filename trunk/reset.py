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
from messager import GMailMessager
import time

def resetServer(clientMail, clientPasswd, serverMail):
    client = GMailMessager(clientMail, clientPasswd, serverMail)
    sessID = int(time.time())
    # send client's 'RESET'
    client.send('RESET/%u' % sessID)
    print 'RESET sent.'
    # wait for server's reply
    while True:
        ms = client.recv()
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
        time.sleep(30)


if __name__ == '__main__':
    clientMail = 'openvpn.nat.user@gmail.com'
    clientPasswd = '********'
    serverMail = 'openvpn.nat.server@gmail.com'

    resetServer(clientMail, clientPasswd, serverMail)
    time.sleep(60)

#############################################################################
#                                                                           #
#   File: address.py                                                        #
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
import socket
import struct

def getMappedAddr(serverList, srcPort):
    BindingRequest = 0x0001
    BindingResponse = 0x0101
    MAPPED_ADDRESS = 0x0001

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(('', srcPort))
    except socket.error:
        # srcPort is in used
        sock.close()
        return 'AddrInUse'

    # send STUN request and wait reply 
    req = struct.pack('!HHLLLL', BindingRequest, 0, 1, 2, 3, 4)
    resp = ''
    sock.settimeout(5)
    for server in serverList:
        sock.sendto(req, (server, 3478))
        try:
            # read response
            resp = sock.recvfrom(1024)[0]
            if len(resp) < 20:
                # wrong response
                continue
            break
        except socket.timeout:
            continue
    if resp == '':
        # failed
        sock.close()
        return ''

    curPos = 0
    # response header
    resp_header = resp[curPos:20]
    curPos += 20
    # get response's status and length
    if struct.unpack('!HHLLLL', resp_header)[0] != BindingResponse:
        sock.close()
        return ''
    resp_data_len = struct.unpack('!HHLLLL', resp_header)[1]
    if resp_data_len == 0:
        sock.close()
        return ''
    if resp_data_len > len(resp) - curPos:
        sock.close()
        return ''
    # read response's attributes one by one
    while resp_data_len >= 4:
        # read attribute header
        attr_header = resp[curPos:curPos + 4]
        curPos += 4
        resp_data_len -= 4
        # get attribute length
        attr_length = struct.unpack('!HH', attr_header)[1]
        if attr_length > 0 and resp_data_len >= attr_length:
            attr_value = resp[curPos:curPos + attr_length]
            curPos += attr_length
            resp_data_len -= attr_length
        # is it MAPPED-ADDRESS?
        if struct.unpack('!HH', attr_header)[0] == MAPPED_ADDRESS:
            # close
            sock.close()
            return '%u.%u.%u.%u/%u' % \
                   (struct.unpack('!HHBBBB', attr_value)[2], 
                   struct.unpack('!HHBBBB', attr_value)[3], 
                   struct.unpack('!HHBBBB', attr_value)[4], 
                   struct.unpack('!HHBBBB', attr_value)[5],
                   struct.unpack('!HHL', attr_value)[1])
    # close
    sock.close()
    return ''

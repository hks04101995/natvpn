#! /usr/bin/env python
#############################################################################
#                                                                           #
#   File: messager.py                                                       #
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
import imaplib
import smtplib
import urllib
import md5
import base64

class Messager:
    'A messager.'
    def __init__(self):
        pass
    def recv(self):
        'Read new messages'
        pass
    def send(self, mesg):
        'Send message'
        pass

class GMailMessager(Messager):
    'A messager based on the GMail.'

    def __init__(self, ourMail, ourPasswd, fromMail):
        Messager.__init__(self)
        self.ourMail = ourMail
        self.ourPasswd = ourPasswd
        self.fromMail = fromMail 

    def recv(self):
        ret_list = []
        # open
        session = imaplib.IMAP4_SSL('imap.gmail.com', 993)
        session.login(self.ourMail, self.ourPasswd)
        # get new mail
        session.select('INBOX')
        typ, data = session.search(None, 'FROM', self.fromMail)
        for num in data[0].split():
            typ, data = session.fetch(num, '(BODY[TEXT])')
            ret_list.append('%s' % data[0][1])
        # delete mail
        typ, data = session.search(None, 'FROM', self.fromMail)
        for num in data[0].split():
           session.store(num, '+FLAGS', '\\Deleted')
        session.expunge()
        # close
        session.close()
        session.logout()
        return ret_list

    def send(self, mesg):
        session = smtplib.SMTP('smtp.gmail.com', 25)
        session.ehlo()
        session.starttls()
        session.ehlo()
        session.login(self.ourMail, self.ourPasswd)
        session.sendmail(self.ourMail, self.fromMail, 
                         'To:null\r\nFrom:null\r\nSubject:null\r\n\r\n' + mesg)
        session.quit()


# for GAppMessager
class GAppMessagerGetChallengeError(Exception):
    pass

class GAppMessagerSendError(Exception):
    pass

class GAppMessagerRecvError(Exception):
    pass

class GAppMessager(Messager):
    'A messager based on the http://dgang.appspot.com/messager.'

    def __init__(self, ourID, ourPasswd, oppositeID):
        Messager.__init__(self)
        self.ourID = ourID
        self.ourPasswd = ourPasswd
        self.oppositeID = oppositeID

    def recv(self):
        params = urllib.urlencode({'user': self.ourID})
        page = urllib.urlopen('http://dgang.appspot.com/messager/auth.py?%s' \
                              % params)
        # get challenge
        challenge = ''
        lineNo = 0
        while True:
            line = page.readline() 
            if line == '':
                break
            # parse line
            line = line.strip()
            lineNo += 1
            if lineNo == 1 and line != '200':
                break
            elif lineNo == 2:
                challenge = line
                break
        # got?
        if challenge == '':
            raise GAppMessagerGetChallengeError, 'Failed to get Challenge.'

        # try to read messages
        mesgs = []
        # compute mac
        m = md5.new()
        m.update(self.ourID)
        m.update(self.ourPasswd)
        m.update(challenge)
        mac = base64.b16encode(m.digest())
        params = urllib.urlencode({'receiver': self.ourID, 
                                   'mac': mac,})
        page = urllib.urlopen('http://dgang.appspot.com/messager/recv.py?%s' \
                              % params)
        # parse response
        lineNo = 0
        while True:
            line = page.readline() 
            if line == '':
                break
            # parse line
            line = line.strip()
            lineNo += 1
            if lineNo == 1 and line != '200':
                raise GAppMessagerRecvError, 'Failed to receive messages.'
            if line.startswith('%s:' % self.oppositeID):
                # Only one mesg is valid for one (receiver, sender) pair.
                mesgs.append(line.partition(':')[2])
                return mesgs
        return mesgs

    def send(self, mesg):
        params = urllib.urlencode({'user': self.ourID})
        page = urllib.urlopen('http://dgang.appspot.com/messager/auth.py?%s' \
                              % params)
        # get challenge
        challenge = ''
        lineNo = 0
        while True:
            line = page.readline() 
            if line == '':
                break
            # parse line
            line = line.strip()
            lineNo += 1
            if lineNo == 1 and line != '200':
                break
            elif lineNo == 2:
                challenge = line
                break
        # got?
        if challenge == '':
            raise GAppMessagerGetChallengeError, 'Failed to get Challenge.'

        # send
        # compute mac
        m = md5.new()
        m.update(self.ourID)
        m.update(self.ourPasswd)
        m.update(challenge)
        m.update(self.oppositeID)
        m.update(mesg)
        mac = base64.b16encode(m.digest())
        params = urllib.urlencode({'sender': self.ourID, 
                                   'receiver': self.oppositeID, 
                                   'content': mesg,
                                   'mac': mac,})
        page = urllib.urlopen('http://dgang.appspot.com/messager/sendto.py?%s' \
                              % params)
        # parse response
        lineNo = 0
        while True:
            line = page.readline() 
            if line == '':
                break
            # parse line
            line = line.strip()
            lineNo += 1
            if lineNo == 1 and line == '200':
                return
        raise GAppMessagerSendError, 'Failed to send message.'


if __name__ == '__main__':
    messager = GAppMessager('client', '***', 'server')
    messager.send('hello')
    messager = GAppMessager('server', '***', 'client')
    print messager.recv()

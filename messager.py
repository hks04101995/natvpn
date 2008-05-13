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

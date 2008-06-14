#! /usr/bin/env python
# coding=utf-8

#############################################################################
#                                                                           #
#   Copyright (C) 2008 Du XiaoGang <dugang@188.com>                         #
#                                                                           #
#   Home: http://dgang.appspot.com                                          #
#                                                                           #
#############################################################################

import wsgiref.handlers
import random
import md5
import base64
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.api import users


class User(db.Model):
    name = db.StringProperty(required=True)
    password = db.StringProperty(required=True)
    challenge = db.StringProperty()


class Message(db.Model):
    receiver = db.StringProperty(required=True)
    sender = db.StringProperty(required=True)
    content = db.StringProperty(required=True)


class InitHandler(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            if user.email() == '***':
                # Discard any message if exist.
                ms = db.GqlQuery('SELECT * from Message')
                for m in ms:
                    m.delete()
                # Remove exist user
                us = db.GqlQuery('SELECT * from User')
                for u in us:
                    u.delete()
                # init
                u = User(name='server', password='***')
                u.put()
                u = User(name='client', password='***')
                u.put()
                # OK, send response
                self.response.headers['Content-Type'] = 'text/plain'
                self.response.out.write('200')
            else:
                # FAILED, send response
                self.response.headers['Content-Type'] = 'text/plain'
                self.response.out.write('403')
        else:
            self.redirect(users.create_login_url(self.request.uri))


class AuthHandler(webapp.RequestHandler):
    def get(self):
        user = self.request.get('user')
        if user == '':
            # invalid request
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('400')
            return
        # Who?
        us = db.GqlQuery('SELECT * FROM User WHERE name = :1', user)
        nu = 0
        for u in us:
            nu += 1
        if nu == 0:
            # invalid user
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('400')
            return
        elif nu != 1:
            # server error
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('500')
            return
        # create challenge
        c = ''
        for i in range(16):
            c += '%02x' % random.randint(0, 255)
        u.challenge = c
        u.put()
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('200\r\n')
        self.response.out.write(c)


class SendtoHandler(webapp.RequestHandler):
    def get(self):
        sender = self.request.get('sender')
        receiver = self.request.get('receiver')
        content = self.request.get('content')
        mac = self.request.get('mac')
        if sender == '' or receiver == '' or content == '' or mac == '':
            # invalid request
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('400')
            return

        # Is sender a valid User?
        us = db.GqlQuery('SELECT * FROM User WHERE name = :1', sender)
        nu = 0
        for senderUser in us:
            nu += 1
        if nu == 0:
            # invalid user
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('400')
            return
        elif nu != 1:
            # server error
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('500')
            return

        # Does sender have got a challenge?
        if senderUser.challenge == '':
            # don't have
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('400')
            return

        # Is receiver a valid User?
        us = db.GqlQuery('SELECT * FROM User WHERE name = :1', receiver)
        nu = 0
        for receiverUser in us:
            nu += 1
        if nu == 0:
            # invalid user
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('400')
            return
        elif nu != 1:
            # server error
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('500')
            return

        # check mac
        m = md5.new()
        m.update(senderUser.name)
        m.update(senderUser.password)
        m.update(senderUser.challenge)
        m.update(receiver)
        m.update(content)
        myMac = base64.b16encode(m.digest())
        if mac != myMac:
            # invalid mac 
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('400')
            return

        # The challenge MUST be used only once.
        # Invalidate senderUser's challenge
        senderUser.challenge = ''
        senderUser.put()

        # put this message into receiver's message queue
        ms = db.GqlQuery('SELECT * FROM Message WHERE receiver = :1 AND sender = :2', 
                         receiver, sender)
        nm = 0
        for mesg in ms:
            nm += 1
        if nm == 0:
            # need create
            mesg = Message(receiver=receiver, sender=sender, content=content)
            mesg.put()
        elif nm == 1:
            # update
            mesg.content = content
            mesg.put()
        else:
            # server error
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('500')
            return

        # OK
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('200')


class RecvHandler(webapp.RequestHandler):
    def get(self):
        receiver = self.request.get('receiver')
        mac = self.request.get('mac')
        if receiver == '' or mac == '':
            # invalid request
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('400')
            return

        # Is receiver a valid User?
        us = db.GqlQuery('SELECT * FROM User WHERE name = :1', receiver)
        nu = 0
        for receiverUser in us:
            nu += 1
        if nu == 0:
            # invalid user
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('400')
            return
        elif nu != 1:
            # server error
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('500')
            return

        # Does receiver have got a challenge?
        if receiverUser.challenge == '':
            # don't have
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('400')
            return

        # check mac
        m = md5.new()
        m.update(receiverUser.name)
        m.update(receiverUser.password)
        m.update(receiverUser.challenge)
        myMac = base64.b16encode(m.digest())
        if mac != myMac:
            # invalid mac 
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('400')
            return

        # The challenge MUST be used only once.
        # Invalidate receiverUser's challenge
        receiverUser.challenge = ''
        receiverUser.put()

        # response
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('200\r\n')
        ms = db.GqlQuery('SELECT * FROM Message WHERE receiver = :1', receiver)
        for mesg in ms:
            # response
            self.response.out.write('%s:%s\r\n' % (mesg.sender, mesg.content))
            mesg.delete()


def main():
    handlers = [('/messager/init.py', InitHandler),
                ('/messager/auth.py', AuthHandler),
                ('/messager/sendto.py', SendtoHandler),
                ('/messager/recv.py', RecvHandler)
               ]
    application = webapp.WSGIApplication(handlers, debug=True)
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()

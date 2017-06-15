import tornado.web
import tornado.ioloop
import os
import sqlite3
import random
import string

def generateRandomString(length):
    s=string.ascii_lowercase+string.digits+string.ascii_uppercase
    return str(''.join(random.sample(s,length)))


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("user")

class MainHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        current_user=str(self.current_user,encoding='utf-8')
        self.render("admin-panel.html", fullname=current_user)
    


class Login(BaseHandler):
    def get(self):
        self.render("login.html")
    
    def post(self):
        username=self.get_argument("username")
        password=self.get_argument("password")
        query='SELECT * FROM "user" WHERE "username"=? AND "password"=?;'
        cur=self.application.db.execute(query,[username,password])
        result=cur.fetchone()
        if not result:
            self.write("نام کاربری یا کلمه عبور اشتباه است")
        else:
            self.set_secure_cookie("user",result[2])
            self.redirect("/")


class Logout(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.clear_cookie("user")
        self.redirect("/login")

class RegisterCustomer(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("register_customer.html")
    
    @tornado.web.authenticated
    def post(self):
        fullname=self.get_argument("fullname")
        phonenumber=self.get_argument("phonenumber")
        address=self.get_argument("address")
        query="INSERT INTO 'customer'('name','address','phonenum') VALUES(?,?,?)"
        cursor=self.application.db.cursor()
        cursor.execute(query,[fullname,address,phonenumber])
        self.application.db.commit()
        self.render("customer-card.html",fullname=fullname,phonenum=phonenumber,address=address,id=cursor.lastrowid)

class Settings(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        query="SELECT * FROM 'settings';"
        cursor=self.application.db.execute(query)
        result=cursor.fetchone()
        self.render("settings.html",settings=result)

    @tornado.web.authenticated
    def post(self):
        rentperiod=self.get_argument("rentperiod")
        rentamount=self.get_argument("rentamount")
        penaltyperiod=self.get_argument("penaltyperiod")
        penaltyamount=self.get_argument("penaltyamount")
        query="UPDATE 'settings' SET 'rentperiod'=?, 'rentamount'=?, 'penaltyperiod'=?, 'penaltyamount'=?;"
        self.application.db.execute(query,[rentperiod,rentamount,penaltyperiod,penaltyamount])
        self.application.db.commit()
        self.redirect("/settings")

if __name__=="__main__":
    settings={
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "template_path": os.path.join(os.path.dirname(__file__), "templates"),
        "login_url": "/login",
        "cookie_secret": generateRandomString(50),
    }

    app=tornado.web.Application([
        (r"/", MainHandler),
        (r"/register", RegisterCustomer),
        (r"/login", Login),
        (r"/logout", Logout),
        (r"/settings", Settings)
    ],**settings)
    app.db=sqlite3.connect("site.db")
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
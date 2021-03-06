import tornado.web
import tornado.ioloop
import os
import sqlite3
import random
import string
import json


def generateRandomString(length):
    s = string.ascii_lowercase + string.digits + string.ascii_uppercase
    return str(''.join(random.sample(s, length)))


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("user")


class MainHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        current_user = str(self.current_user, encoding='utf-8')
        self.render("admin-panel.html", fullname=current_user)


class Login(BaseHandler):
    def get(self):
        self.render("login.html", message=None)

    def post(self):
        username = self.get_argument("username")
        password = self.get_argument("password")
        query = 'SELECT * FROM "user" WHERE "username"=? AND "password"=?;'
        cur = self.application.db.execute(query, [username, password])
        result = cur.fetchone()
        if not result:
            self.render("login.html", message=True)
        else:
            self.set_secure_cookie("user", result[2])
            self.redirect("/")


class Logout(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.clear_cookie("user")
        self.redirect("/login")


class RegisterCustomer(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("register-customer.html")

    @tornado.web.authenticated
    def post(self):
        fullname = self.get_argument("fullname")
        phonenumber = self.get_argument("phonenumber")
        address = self.get_argument("address")
        query = "INSERT INTO 'customer'('name','address','phonenum') VALUES(?,?,?)"
        cursor = self.application.db.cursor()
        cursor.execute(query, [fullname, address, phonenumber])
        self.application.db.commit()
        self.render("customer-card.html", fullname=fullname,
                    phonenum=phonenumber, address=address, id=cursor.lastrowid)


class Settings(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        query = "SELECT * FROM 'settings';"
        cursor = self.application.db.execute(query)
        result = cursor.fetchone()
        self.render("settings.html", settings=result)

    @tornado.web.authenticated
    def post(self):
        rentperiod = self.get_argument("rentperiod")
        rentamount = self.get_argument("rentamount")
        penaltyperiod = self.get_argument("penaltyperiod")
        penaltyamount = self.get_argument("penaltyamount")
        query = "UPDATE 'settings' SET 'rentperiod'=?, 'rentamount'=?, 'penaltyperiod'=?, 'penaltyamount'=?;"
        self.application.db.execute(
            query, [rentperiod, rentamount, penaltyperiod, penaltyamount])
        self.application.db.commit()
        self.redirect("/settings")


class AddProductTitle(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("add-product-title.html")

    @tornado.web.authenticated
    def post(self):
        title = self.get_argument("title")
        genre = self.get_argument("genre")
        number = self.get_argument("number")
        product_type = self.get_argument("type")

        if number == "":
            number = "0"

        if product_type not in ["game", "film"]:
            self.write("تلاش برای نفوذ امنیتی")

        query = "INSERT INTO 'products'('title','genre','number','type') VALUES(?,?,?,?);"
        cursor = self.application.db.cursor()
        cursor.execute(query, [title, genre, number, product_type])

        if product_type == "film":
            product_type = "فیلم"
        else:
            product_type = "بازی"

        self.application.db.commit()
        self.render("product-label.html", title=title, genre=genre,
                    type=product_type, id=cursor.lastrowid)


class SearchTitle(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("search-title.html")

    @tornado.web.authenticated
    def post(self):
        product_id = self.get_argument("product_id")
        self.redirect("/show_product_info/" + product_id)


class AddOrRemoveDisks(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("add-or-remove-disks.html")

    def post(self):
        disk_numbers = self.get_argument("disk_numbers")
        query = "UPDATE 'products' SET number=? WHERE id=?;"
        product_id = str(self.get_secure_cookie(
            "product_id"), encoding='utf-8')
        self.clear_cookie("product_id")
        self.application.db.execute(query, [disk_numbers, product_id])
        self.application.db.commit()

        self.redirect("/show_product_info/{}".format(product_id))


class NumberOfDisks(BaseHandler):
    # this class responds to ajax request
    @tornado.web.authenticated
    def post(self):
        title_id = self.get_argument("title_id")
        query = "SELECT * FROM 'products' WHERE id=?;"
        cursor = self.application.db.execute(query, [title_id])
        result = cursor.fetchone()
        if result == None:
            data = {
                "message": "محصولی با شناسه مورد نظر یافت نشد."
            }
            json_data = json.dumps(data)
            self.write(str(json_data))
        else:
            data = {
                "id": result[0],
                "title": result[1],
                "genre": result[2],
                "number": result[3],
                "type": result[4],
                "message": "None",
            }
            self.set_secure_cookie("product_id", str(result[0]))
            json_data = json.dumps(data)
            self.write(str(json_data))


class ShowProductInfo(BaseHandler):
    @tornado.web.authenticated
    def get(self, product_id):
        query = "SELECT * FROM 'products' WHERE id=?;"
        cursor = self.application.db.execute(query, [product_id])
        product_info = cursor.fetchone()
        if product_info == None:
            return self.render("message.html", message="محصولی با شناسه مورد نظر یافت نشد.",
                               return_path="/search_title")

        query = """
        SELECT DISTINCT customer_id, rent_date, name, phonenum
        FROM rent JOIN customer ON rent.customer_id=customer.id 
        WHERE product_id=? AND return_date IS NULL;
        """
        rent_info = self.application.db.execute(query, [product_id]).fetchall()

        self.render("show-product-info.html",
                    product_info=product_info, rent_info=rent_info)


class RentProducts(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("rent-product.html")

    @tornado.web.authenticated
    def post(self):
        customer_id = self.get_argument("customer_id")
        query = "SELECT * FROM customer WHERE id=?"
        cursor = self.application.db.execute(query, [customer_id])
        customer = cursor.fetchone()

        if customer == None:
            return self.render("message.html", message="مشتری با شناسه مورد نظر یافت نشد.",
                               return_path="/rent_products")
        ids_string = self.get_argument("product_ids")
        ids_list = ids_string.split(',')

        products = []

        for id in ids_list:
            query = "SELECT * FROM products WHERE id=?"
            cursor = self.application.db.execute(query, [id])
            product = cursor.fetchone()
            if product == None:
                return self.render("message.html", message="محصولی با شناسه %s یافت نشد" % (id),
                                   return_path="/rent_products")
            products.append(product)

        for id in ids_list:
            query = "INSERT INTO rent(customer_id, product_id, rent_date) VALUES(?,?,DATE('now'));"
            self.application.db.execute(query, [customer_id, id])
            self.application.db.commit()

        self.render("rent-information.html",
                    products=products, customer=customer)


class ReturnProducts(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("return-products.html")

    @tornado.web.authenticated
    def post(self):
        customer_id = self.get_argument("customer_id")
        query = "SELECT * FROM customer WHERE id=?"
        cursor = self.application.db.execute(query, [customer_id])
        customer = cursor.fetchone()

        if customer == None:
            return self.render("message.html", message="مشتری با شناسه مورد نظر یافت نشد.",
                               return_path="/return_products")

        ids_string = self.get_argument("product_ids")
        ids_list = ids_string.split(',')
        products = []
        for id in ids_list:
            query = "SELECT * FROM rent WHERE customer_id=? AND product_id=? AND return_date IS NULL;"
            select_product_query = "SELECT * FROM products WHERE id=?"
            cursor = self.application.db.execute(query, [customer_id, id])
            result = cursor.fetchone()
            if result == None:
                return self.render("message.html", message="محصولی با شناسه %s به مشتری مورد نظر اجاره داده نشده است" % (id),
                                   return_path="/rent_products")
            select_product_query = "SELECT * FROM products WHERE id=?"
            cursor = self.application.db.execute(select_product_query, [id])
            product = cursor.fetchone()
            products.append(product)

        for id in ids_list:
            query = "UPDATE rent SET return_date=DATE('now') WHERE customer_id=? AND product_id=? AND return_date IS NULL;"
            self.application.db.execute(query, [customer_id, id])
            self.application.db.commit()

        self.render("rent-information.html",
                    products=products, customer=customer)


class About(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        self.render("about.html")

if __name__ == "__main__":
    settings = {
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "template_path": os.path.join(os.path.dirname(__file__), "templates"),
        "login_url": "/login",
        #"cookie_secret": generateRandomString(50),
        "cookie_secret": "generateRandomString(50)",
    }

    app = tornado.web.Application([
        (r"/", MainHandler),
        (r"/register", RegisterCustomer),
        (r"/login", Login),
        (r"/logout", Logout),
        (r"/settings", Settings),
        (r"/add_product_title", AddProductTitle),
        (r"/search_title", SearchTitle),
        (r"/add_or_remove_disks", AddOrRemoveDisks),
        (r"/number_of_disks", NumberOfDisks),
        (r"/show_product_info/([0-9]+)", ShowProductInfo),
        (r"/rent_products", RentProducts),
        (r"/return_products", ReturnProducts),
        (r"/about", About),
    ], **settings)
    app.db = sqlite3.connect("site.db")
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()

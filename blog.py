from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

# Kullanıcı Kayıt Formu
class RegisterForm(Form):
    name = StringField("İsim Soyisim", validators=[validators.length(min=4, max=50, message="En az 4 en fazla 50 karakter girin!")])
    username = StringField("Kullanıcı Adı", validators=[validators.length(min=5, max=16, message="En az 5 en fazla 16 karakter girin!")])
    email = StringField("E-mail", validators=[validators.Email(message="Lütfen geçerli bir mail adresi girin!")])
    password = PasswordField("Parola", validators=[
        validators.data_required("Lütfen bir parola girin!"),
        validators.EqualTo(fieldname="confirm", message="Parolanız uyuşmuyor!")
    ])
    confirm = PasswordField("Parola Doğrula", validators=[
        validators.data_required("Lütfen bir parola girin!"),
        validators.EqualTo(fieldname="password", message="Parolanız uyuşmuyor!")
    ])

# Login formu
class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")

# Makale Formu
class ArticleForm(Form):
    title = StringField("Başlık", validators=[validators.length(min=5, max=100, message="Başlık en az 5 en fazla 10 karakterden oluşmalı!")])
    content = TextAreaField("Makale İçeriği", validators=[validators.length(min=10, message="İçerik en an 10 karakterden oluşmalı!")])


# Kullanıcı giriş decorator
def login_req(f):
    @wraps(f)
    def decorated_func(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için giriş yapmalısınız!", "danger")
            return redirect(url_for("login"))
    return decorated_func
app = Flask(__name__)
app.secret_key = "myblog"

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "myblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

sql = MySQL(app)

@app.route("/")
def index():
    return render_template("index.html", answer = "hayır")
@app.route("/about")
def about():
    return render_template("about.html")
#Register
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm(request.form)

    if(request.method == "POST" and form.validate()):
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = sql.connection.cursor()

        sorgu = "insert into users(name, email, username, password) values(%s, %s, %s, %s)"

        cursor.execute(sorgu, (name, email, username, password))
        sql.connection.commit()
        cursor.close()

        flash(message="Başarılı bir şekilde kayıt olundu.", category="success")

        return redirect(url_for("login"))
    else:
        return render_template("register.html", form = form)

#Login
@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password = form.password.data

        cursor = sql.connection.cursor()
        sorgu = "select * from users where username = %s"
        result = cursor.execute(sorgu, (username,))
        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password, real_password):
                flash("Başarıyla giriş yaptınız.", "success")
                session["logged_in"] = True
                session["username"] = data["username"]
                return redirect(url_for("index"))
            else:
                flash("Parolanızı yanlış girdiniz!", "danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle bir kullanıcı bulunamadı", "danger")
            return redirect(url_for("login"))

    return render_template("login.html", form = form)

# logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# dashboard
@app.route("/dashboard")
@login_req
def dashboard():
    cursor = sql.connection.cursor()

    sorgu = "select * from articles where author = %s"

    result = cursor.execute(sorgu, (session["username"],))

    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html", articles = articles)
    else:
        return render_template("dashboard.html")

# Makale Ekle
@app.route("/addarticle", methods = ["GET", "POST"])
def addarticle():
    form = ArticleForm(request.form)

    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = sql.connection.cursor()
        sorgu = "insert into articles(title, author, content) values(%s, %s, %s)"

        cursor.execute(sorgu, (title, session["username"], content))
        sql.connection.commit()

        cursor.close()

        flash("Makale başarıyla kaydedildi.", "success")

        return redirect(url_for("dashboard"))
    return render_template("addarticle.html", form = form)

@app.route("/articles")
def articles():
    cursor = sql.connection.cursor()
    sorgu = "select * from articles"
    result = cursor.execute(sorgu)

    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html", articles = articles)
    else:
        return render_template("articles.html")

# Detay sayfası
@app.route("/article/<string:id>")
def detail(id):
    cursor = sql.connection.cursor()

    sorgu = "select * from articles where id = %s"

    result = cursor.execute(sorgu, (id,))

    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html", article = article)
    else:
        return render_template("article.html")

# Makale Silme
@app.route("/delete/<string:id>")
@login_req
def delete(id):
    cursor = sql.connection.cursor()

    sorgu = "select * from articles where author = %s and id = %s"

    result = cursor.execute(sorgu, (session["username"], id))
    if result > 0:
        sorgu2 = "delete from articles where author = %s and id = %s"
        cursor.execute(sorgu2, (session["username"], id))
        sql.connection.commit()
        flash("Makale başarıyla silindi.", "success")
        return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok veya bu makaleyi silmeye yetkiniz yok!", "danger")
        return redirect(url_for("index"))

# Makale Düzenle
@app.route("/edit/<string:id>", methods = ["GET", "POST"])
@login_req
def update(id):

    if request.method == "GET":
        cursor = sql.connection.cursor()

        sorgu = "select * from articles where author = %s and id = %s"

        result = cursor.execute(sorgu, (session["username"], id))

        if result > 0:
            article = cursor.fetchone()
            form = ArticleForm()

            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("edit.html", form = form)
        else:
            flash("Böyle bir makale yok ya da bu makaleyi düzenlemeye yetkiniz yok!", "danger")
            return render_template("index.html")
    else:
        form = ArticleForm(request.form)
        newTitle = form.title.data
        newContent = form.content.data

        sorgu = "update articles set title = %s, content = %s where id = %s"

        cursor = sql.connection.cursor()

        cursor.execute(sorgu, (newTitle, newContent, id))

        sql.connection.commit()

        flash("Makale başarıyla güncellendi.", "success")
        return redirect(url_for("dashboard"))

# Arama
@app.route("/search", methods = ["GET", "POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        sorgu = "select * from articles where title like '%" + keyword + "%'"

        cursor = sql.connection.cursor()

        result = cursor.execute(sorgu)

        if result == 0:
            flash("Aranan kelimeye uygun makale bulunamadı!", "warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html", articles = articles)
        cursor.execute(sorgu)
if __name__ == "__main__":
    app.run(debug = True)
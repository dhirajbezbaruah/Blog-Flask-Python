from flask import Flask, render_template, request, flash, redirect, url_for, session, logging, flash
from wtforms import StringField, PasswordField, validators, Form, DateField, ValidationError
from flask_mysqldb import MySQL
from passlib.hash import sha256_crypt
from functools import wraps
from flask_mail import Mail, Message
from flask_wtf.file import FileAllowed, FileField
import secrets
import os
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, TimedJSONWebSignatureSerializer
#import safe
from werkzeug.utils import secure_filename
from PIL import Image


app=Flask(__name__)
#mysql config
app.config['MYSQL_HOST'] ='localhost'
app.config['MYSQL_USER'] ='root'
app.config['MYSQL_PASSWORD'] ='1111'
app.config['MYSQL_DB'] ='myflaskapp'
app.config['MYSQL_CURSORCLASS'] ='DictCursor'

mysql=MySQL(app)



#mail server config
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'dbezbaruah412@gmail.com'
app.config['MAIL_PASSWORD'] = 'adtu2k15'
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

s= URLSafeTimedSerializer('secret123')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('You Must Login First!', 'danger')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

#Home
@app.route("/")
def index():
    return render_template('index.html')

def validates(RegisterForm, password):
    p=password.data
    #spec= "!@#$%&_="
    if not any(i.isdigit() for i in p):
        raise ValidationError('Password must contain numbers and letters')
    elif len(p)<6:
        raise ValidationError('Minimum length of password should be 6')

def valid(RegisterForm, password):
    sp_cha=('!', '@', '#', '$', '%')
    for i in password.data:
        if i not in sp_cha:
            
            raise ValidationError('sp')


class RegisterForm(Form):
    
    name=StringField('Name', [validators.DataRequired(), validators.Length(min=1, max=50)])
    username= StringField('username', [validators.DataRequired(), validators.Length(min=4, max=50)])
    email=StringField('Email', [validators.DataRequired(), validators.Length(min=6, max=100)])
    password= PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match!'),
        validates
    ])
    confirm=PasswordField('Confirm password', [validators.DataRequired()])


@app.route('/register', methods=['GET', 'POST'])
def register():
    
    form=RegisterForm(request.form)
    if request.method=='POST' and form.validate():
        name=form.name.data
        email=form.email.data
        username=form.username.data
        password=sha256_crypt.encrypt(str(form.password.data))
        confirm_email='0'


        cur= mysql.connection.cursor()
        
        cur.execute("SELECT * FROM users WHERE email = %s", [email])

        if cur.fetchone() is not None:
            flash("Email Already registered :D, Login to continue", 'danger')
            return redirect(url_for('login'))
        
        
    
        cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if cur.fetchone() is not None:
            flash("Username already taken", 'danger')
            

        else:
            cur.execute("INSERT INTO users(name, email, username, password, confirm_email) VALUES(%s, %s, %s, %s, %s)", (name, email, username, password, confirm_email))
        
            mysql.connection.commit()
            token= s.dumps(email, salt='email-confirm')
            msg=Message('Confirm Email', sender='dbezbaruah412@gmail.com', recipients=[email])
            link=url_for('confirm_email', token=token, _external=True)
            msg.body='Thanks For siging up. Please click on the link to activate your account. The link will be expired in 1 hour. {}'.format(link)
            mail.send(msg)
        
            flash('Please confirm your email', 'success')
            return redirect(url_for('login'))
        

        cur.close()

        

        
    return render_template('register.html', form=form)
    
@app.route('/confirm_email/<token>')

def confirm_email(token):
    try:
        email=s.loads(token, salt='email-confirm', max_age=3600)
    except SignatureExpired:
        return 'Your Link is Expired'
    cur=mysql.connection.cursor()
    result=cur.execute("SELECT * FROM users where confirm_email= %s", [confirm_email])
    
    #cur.close()
    if result>0:
        return 'confirmed'
    else:
        cur=mysql.connection.cursor()
        cur.execute("UPDATE users SET confirm_email='1' where email=%s", [email])
        mysql.connection.commit()
        cur.close()
        flash('Email confirmed! You can now login.', 'success')
    return redirect(url_for('login'))

####LOGINNNN

class LoginForm(Form):
    usernamelogin=StringField('Username/Email', [validators.Length(min=1, max=50)])
    passwordlogin=PasswordField('Password', [validators.DataRequired(), validators.Length(min=3, max=100)])


@app.route('/login', methods=['GET', 'POST'])
def login():
    formlogin=LoginForm(request.form)
    if request.method=='POST' and formlogin.validate():
        usernamelogin=formlogin.usernamelogin.data
        emaillogin=formlogin.usernamelogin.data
        passwordlogin=formlogin.passwordlogin.data

        cur=mysql.connection.cursor()
        result=cur.execute("SELECT * FROM users where username= %s", [usernamelogin])
        #result2=cur.execute("SELECT * FROM users where email=%s", [usernamelogin])
        if result>0:
            data = cur.fetchone()
            password= data['password']

            if sha256_crypt.verify(passwordlogin, password) and  (cur.execute("SELECT * FROM users where confirm_email='1' and password=%s", [password])):
                session['logged_in']= True
                session['username']= usernamelogin
                cur.execute("SELECT email FROM users where username= %s",[session['username']] )
                res=cur.fetchone()
                email=res['email']
                session['email']= email
                
                flash('you are now logged in', 'success')
                return redirect(url_for('index'))
            elif sha256_crypt.verify(passwordlogin, password) and  (cur.execute("SELECT * FROM users where confirm_email='0'  and password=%s", [password])):
                session['logged_in']= False
                session.clear()
                return redirect(url_for('unconfirmed'))

            else:
                flash("Password didnot match", 'danger')
                return redirect(url_for('login'))
            return redirect(url_for('login'))
        elif (cur.execute("SELECT * FROM users where email=%s", [emaillogin]))>0:
        
            data = cur.fetchone()
            password= data['password']

            if sha256_crypt.verify(passwordlogin, password) and  (cur.execute("SELECT * FROM users where confirm_email='1' and password=%s", [password])):
                session['logged_in']= True
                #session['username']= usernamelogin
                session['email'] = emaillogin

                cur.execute("SELECT username FROM users where email= %s",[session['email']] )
                res=cur.fetchone()
                username=res['username']
                session['username']= username

                


                flash('you are now logged in', 'success')
                return redirect(url_for('index'))
            elif sha256_crypt.verify(passwordlogin, password) and  (cur.execute("SELECT * FROM users where confirm_email='0'  and password=%s", [password])):
                #flash("confirm email first")
                session['logged_in']= False
                session.clear()
                return redirect(url_for('unconfirmed'))

            else:
                flash("Password didnot match", 'danger')
                return redirect(url_for('login'))
        else:
            flash('Username not found', 'danger')
            return redirect(url_for('login'))
        

        cur.close()
    else:
        #flash('Username not found', 'danger')
        return render_template('login.html', formlogin=formlogin)

        


    #return render_template('login.html', formlogin=formlogin)

@app.route("/logout")
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

@app.route('/unconfirmed')
def unconfirmed():
    return render_template('unconfirmed.html')

class forget_form(Form):
    email=StringField('',[validators.DataRequired(), validators.Length(min=4, max=30)])

@app.route("/forget_password", methods=['GET', 'POST'])
def forget_password():
    formforget=forget_form(request.form)
    if request.method=='POST' and formforget.validate():
        emailforget=formforget.email.data
        cur= mysql.connection.cursor()
        
        cur.execute("SELECT * FROM users WHERE email = %s", [emailforget])
        if cur.fetchone() is not None:
            tokenforget= s.dumps(emailforget, salt='forget_pass')
            msg1=Message('Reset Password', sender='dbezbaruah412@gmail.com', recipients=[emailforget])
            link1=url_for('reset_password', tokenforget=tokenforget, _external=True)
            msg1.body='Please click in the link below to reset your password {}'.format(link1)
            mail.send(msg1)
        flash('Password reset link has been sent to your registered email', 'success')
        return redirect(url_for('forget_password'))

    return render_template('forget_password.html', formforget=formforget)


class resetform(Form):
    password=PasswordField('New password', [validators.DataRequired(), validators.Length(min=4, max=44)])


@app.route("/reset_password/<tokenforget>", methods=['GET', 'POST'])
def reset_password(tokenforget):
    formreset=resetform(request.form)
    if request.method=='POST' and formreset.validate():
        password= sha256_crypt.encrypt(str(formreset.password.data))
        try:
            email=s.loads(tokenforget, salt='forget_pass', max_age=3600)
            cur=mysql.connection.cursor()
            cur.execute("SELECT * FROM users WHERE email=%s", [email])
            if cur.fetchone() is not None:
                cur.execute("UPDATE users SET password=%s where email=%s", [password, email])
                mysql.connection.commit()
                flash('password updated', 'success')
            return redirect(url_for('login'))
        
        except SignatureExpired:
            return 'Token Expired'


    #password= formreset.newpassword.data
    
    return render_template('reset_password.html', formreset=formreset)

#Dashboard
class DateForm(Form):
    dt = DateField('date', format='%Y-%m-%d')

@app.route('/dashboard', methods=['POST','GET'])
@login_required
def dashboard():
    formdate=DateForm(request.form)
    if request.method=='POST':
        dt=formdate.dt.data
        #then = dt.strftime('%Y-%m-%d %H-%M-%S')
        #then=str(dt)
        #formatted_date = dt.strftime('%Y-%m-%d')

        cur=mysql.connection.cursor()
        cur.execute("INSERT INTO record (date) VALUES('%s')", (dt))
        mysql.connection.commit()
        #cur.close()

    return render_template('dashboard.html', formdate=formdate)



#User Profile
class userprofile(Form):
    name=StringField('Name', [validators.DataRequired(), validators.Length(min=1, max=50)])
    username= StringField('username', [validators.DataRequired(), validators.Length(min=4, max=50)])
    email=StringField('Email', [validators.DataRequired(), validators.Length(min=6, max=100)])

class profile_pic(Form):
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png'])])
    #submit = SubmitField('Update')



UPLOAD_FOLDER = 'static\\profile_pic'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/profile', methods=['POST','GET'])
@login_required
def profile():
    cur=mysql.connection.cursor()

     

    cur.execute("SELECT name FROM users where email= %s",[session['email']] )
    res=cur.fetchone()
    name=res['name']
    

    uprofile=userprofile(request.form)
    dpform=profile_pic(request.form)
    if request.method == 'POST':
        uprofile.email.data = session['email']
        uprofile.username.data = session['username']
        uprofile.name.data = name
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file ')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            cur=mysql.connection.cursor()
            cur.execute("UPDATE users SET dp=%s where username=%s", [filename, session['username']])
            mysql.connection.commit()
            cur.execute("SELECT dp FROM users where username= %s",[session['username']] )
            res=cur.fetchone()
            dp=res['dp']
            session['dp']= dp
        if file and not allowed_file(file.filename):
            flash('invalid image file')

            #return redirect(url_for('uploaded_file',
                                    #filename=filename))
    if request.method=='GET':
        uprofile.email.data = session['email']
        uprofile.username.data = session['username']
        uprofile.name.data = name
        cur.execute("SELECT dp FROM users where username= %s",[session['username']] )
        res=cur.fetchone()
        dp=res['dp']
        session['dp']= dp
        dpform.picture.data=session['dp']

        

    #cur=mysql.connection.cursor()
    #profile_image = url_for('static', filename='profile_pic/'+ str(cur.execute("SELECT dp FROM users WHERE email=%s", [session['username']])))
    return render_template('userprofile.html', uprofile=uprofile, dpform=dpform)

######TESTING BELOW-----DONT GO######
    


def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))



@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('uploaded_file',
                                    filename=filename))
    return render_template('upload.html')
    '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>'''


from flask import send_from_directory

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)

####END of TESTING####

if __name__ == "__main__":
    app.secret_key='secret123'
    app.run(debug=True)

    
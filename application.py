from flask import Flask, render_template, request, url_for, redirect
from flask import flash, jsonify
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from models import Base, User, Task, StudentTask
from flask import session as login_session
import random
import string

#IMPORTS REQUIRED FOR APPLYING OAuth2
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
       open('client_secrets.json', 'r').read())['web']['client_id']
Application_NAME = "sudanMentors"

#connect to the database and create a dtabase session
engine = create_engine('sqlite:///studentsmentors.db?check_same_thread=False')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/login')
def showLogin():
       state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                       for x in range(32))
       login_session['state'] = state
       return render_template('login.html', STATE=state)

@app.route('/gconnect', methods=['POST', 'GET'])
def gconnect():
       # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is'
                                 'already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()
    # login_session['provider'] = 'google'
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    login_session['role'] = 'user'
    

    # see if a user exists, if not make a new one

    user_id = getUserID(login_session['email'])
    if not user_id:
            
        user_id = createUser(login_session)
        #createAdmin(login_session['email'])
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;'
    '-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

@app.route('/gdisconnect')
def gdisconnect():
    access_token = login_session.get('access_token')
    if access_token is None:
        print 'Access Token is None'
        response = make_response(json.dumps('Current user not connected.'),
                                 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    print 'In gdisconnect access token is %s', access_token
    print 'User name is: '
    print login_session['username']
    url = ('https://accounts.google.com/o/oauth2/revoke?token=%s'
           % login_session['access_token'])
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    print 'result is '
    print result
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['role']
        
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke token for'
                                 'given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response

# User Helper Functions

def createUser(login_session):
       newUser = User(name=login_session['username'], email=login_session[
                      'email'], picture=login_session['picture'],role=login_session['role'])
       session.add(newUser)
       session.commit()
       user = session.query(User).filter_by(email=login_session['email']).one()
       return user.id
def getUserInfo(user_id):
       user = session.query(User).filter_by(id=user_id).one
       return user

def getUserID(email):
       try:
              user = session.query(User).filter_by(email=email).one()
              return user.id
       except:
              return None
       

              
@app.route('/')
def showHome():
	#return("this page to show home page")
       return render_template('home.html')
@app.route('/welcome')
def welcomeUser():
       if 'username' not in login_session:
              return redirect('/')
       userID=login_session['user_id']
       user = session.query(User).filter_by(id=userID).one()
       if user.role== 'user':
              return"You Are Not Registered Yet"
       elif user.role=='student':
              studentTasks=session.query(StudentTask).filter_by(student_id=user.id).all()
              if user.mentor_id:
                     mentor=session.query(User).filter_by(id=user.mentor_id).one()
                     return render_template('studenPage.html',user=user,mentor=mentor,studentTasks=studentTasks)
              return render_template('studenPage.html',user=user,mentor=None,studentTasks=studentTasks)
       elif user.role=='mentor':
              students=session.query(User).filter_by(mentor_id=user.id).all()
              return render_template('mentorPage.html', students=students,mentorID=user.id)
       elif user.role=='admin':
              return render_template('adminPage.html')
@app.route('/admin/users', methods = ['GET'])
def showUsers():
       if 'username' not in login_session:
              return redirect('/')
       userID=login_session['user_id']
       user = session.query(User).filter_by(id=userID).one()
       if user.role == 'admin':
              users=session.query(User).all()
              if users:
                     return render_template('showusers.html', users=users)
              else:
                     return"there are no users to show"
       else:
              return redirect(url_for('welcomeUser'))
       
@app.route('/admin/users/<int:userID>')
def showUser(userID):
       #return "this page is to show user informations"
       if 'username' not in login_session:
              return redirect('/')
       currentUserID=login_session['user_id']
       currentUser= session.query(User).filter_by(id=currentUserID).one()
       if currentUser.role=='admin':
              user=session.query(User).filter_by(id=userID).one()
              return render_template('showuser.html',user=user)
       else:
              return redirect(url_for('welcomeUser'))
@app.route('/admin/users/<int:userID>/edit', methods=['GET','POST'])
def editUser(userID):
       #if 'username' not in login_session:
              #return redirect('/')
       #adminID=login_session['user_id']
       #user = session.query(User).filter_by(id=adminID).one()
       #if user.role=='admin':
              userToEdit=session.query(User).filter_by(id=userID).one()
              if request.method=='POST':
                     if request.form['role']:
                            userToEdit.role = request.form['role']
                     if request.form['id']:
                            userToEdit.mentor_id= request.form['id']
                     if request.form['phone']:
                            userToEdit.phone= request.form['phone']
                     session.add(userToEdit)
                     session.commit()
                     return redirect(url_for('showUser',userID=userToEdit.id))
              else:
                     return render_template('edituser.html', user=userToEdit)
       #else:
              #return redirect(url_for('welcomeUser'))
       
              
       
@app.route('/admin/users/<int:userID>/delete', methods=['GET','POST'])
def deleteUser(userID):
       if 'username' not in login_session:
              return redirect('/')
       currentUserID=login_session['user_id']
       currentUser=session.query(User).filter_by(id=currentUserID).one()
       if currentUser.role=='admin':
              #return"here we delete the user"
              userToDelete=session.query(User).filter_by(id=userID).one()
              if request.method=='POST':
                     session.delete(userToDelete)
                     session.commit()
                     return redirect(url_for('showUsers'))
              else:
                     return render_template('deleteuser.html', user=userToDelete)
       else:
              return redirect(url_for('welcomeUser'))

@app.route('/admin/users/add', methods=['GET','POST'])
def addUser():
       if 'username' not in login_session:
              return redirect('/')
       currentUserID=login_session['user_id']
       currentUser=session.query(User).filter_by(id=currentUserID).one()
       if currentUser.role=='admin':
              #return'here we add a user'
              if request.method=='POST':
                     if request.form['name']:
                            newUser=User(name=request.form['name'])
                     if request.form['email']:
                            newUser.email=request.form['email']
                     if request.form['role']:
                            newUser.role=request.form['role']
                     session.add(newUser)
                     session.commit()
                     return redirect(url_for(showUsers))
              else:
                     return render_template('addUser.html')
       else:
              return redirect(url_for('welcomeUser'))

@app.route('/admin/task/add', methods=['GET','POST'])
def addTask():
       if request.method=='POST':
              if request.form['name']:
                     newTask=Task(name=request.form['name'], added='False')
              if request.form['date']:
                     newTask.date=request.form['date']       
              session.add(newTask)
              session.commit()
              return redirect(url_for('showTasks'))
       else:
              return render_template('addtask.html')
@app.route('/admin/task/show')
def showTasks():
       tasks=session.query(Task).all()
       return render_template('showtasks.html', tasks=tasks)
@app.route('/admin/task/<int:taskID>/delete', methods= ['GET','POST'])
def deleteTask(taskID):
       taskToDelete=session.query(Task).filter_by(id=taskID).one()
       if request.method=='POST':
              session.delete(taskToDelete)
              session.commit()
              return redirect(url_for('showTasks'))
       else:
              return render_template('deletetask.html',task=taskToDelete)

@app.route('/admin/task/<int:taskID>/addtoallstudents', methods=['GET','POST'])
def addTaskToAllStudents(taskID):
       task = session.query(Task).filter_by(id=taskID).one()
       if request.method == 'POST':
              students=session.query(User).filter_by(role='student').all()
              for student in students:
                     newTask= StudentTask(name=task.name, date=task.date, student_id=student.id,task_id=task.id, status='pending')
                     session.add(newTask)
                     session.commit()
              task.added='True'
              session.add(task)
              session.commit()
              return redirect(url_for('showTasks'))
       else:
              return render_template('addtasktoallstudents.html', task=task)
@app.route('/admin/task/<int:taskID>/deletetoallstudents', methods=['GET','POST'])
def deleteTaskToAllStudents(taskID):
       originalTask= session.query(Task).filter_by(id=taskID).one()
       tasksToDelete = session.query(StudentTask).filter_by(task_id=taskID).all()
       if request.method=='POST':
              for task in tasksToDelete:
                     session.delete(task)
                     session.commit()
              originalTask.added='False'       
              return redirect(url_for('showTasks'))
       else:
              return render_template('deletetasktoallstudents.html',taskID=taskID)
       
@app.route('/student/task/show')
def showAllStudentTasks():
       studentTasks=session.query(StudentTask).all()
       return render_template('showallstudenttasks.html', studentTasks=studentTasks)

@app.route('/welcome/mentor/<int:mentorID>/student/<int:studentID>')
def showStudent(mentorID,studentID):
       #show student information to his mentor
       student= session.query(User).filter_by(id=studentID).one()
       if student.mentor_id==mentorID:
              tasks=session.query(StudentTask).filter_by(student_id=studentID).all()
              return render_template('showstudent.html',tasks=tasks,studentID=studentID,mentorID=mentorID)
       else:
               return"this is not your student"

@app.route('/mentor/<int:mentorID>/student/<int:studentID>/mark/<int:studentTaskID>/done')
def markAsDone(studentID,mentorID,studentTaskID):
       student=session.query(User).filter_by(id=studentID).one()
       if student.mentor_id==mentorID:
              taskToMark=session.query(id=studentTaskID).one()
              if request.method=='POST':
                     taskToMark.status='Done'
                     session.add(taskToMark)
                     session.commit()
                     return redirect(url_for('showStudent',studentID=studentID,mentorID=mentorID))
              else:
                     return render_template('marktaskasdone.html',studentID=studentID,mentorID=mentorID,studentTaskID=studentTaskID)
              
       else:
              return "you are not allowed to change this task"
              
if __name__ == '__main__':
        app.secret_key = 'super_secret_key'
	app.debug = True
	app.run(host='0.0.0.0', port=8000)		
 

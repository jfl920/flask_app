# Import the flask module and create an app using Flask as shown
# we'll use to render the template files
# In order to read the posted values we need to import request from Flask.

from flask import Flask, render_template, json, request, redirect, session
from flask.ext.mysql import MySQL
from werkzeug import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'why would I tell you my secret key??'

mysql = MySQL()
# MySQL configurations
app.config['MYSQL_DATABASE_USER'] = 'root'
#app.config['MYSQL_DATABASE_PASSWORD'] = ''
app.config['MYSQL_DATABASE_DB'] = 'BucketList'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

# default settings
pageLimit = 2

# Now define the basic route / and its corresponding request handler:
@app.route("/")
# Modify the main method to return the rendered template file
def main():
    return render_template('index.html')

@app.route('/showSignUp')
def showSignUp():
# render the signup page once a request comes to /showSignUp
    return render_template('signup.html')

@app.route('/signUp', methods=['POST', 'GET'])
def signUp():

	try:
	    # read the posted values from the UI
	    _name = request.form['inputName']
	    _email = request.form['inputEmail']
	    _password = request.form['inputPassword']

	    # validate the received values
	    if _name and _email and _password:

	    	# All Good, let's create MySQL connection
	    	conn = mysql.connect()

	    	# cursor to query stored procedure
	    	cursor = conn.cursor()
	    	
	    	# use salting module to created hashed password
	    	_hashed_password = generate_password_hash(_password)
	    	
	    	# call procedure sp_createUser
	    	cursor.callproc('sp_createUser', (_name, _email, _hashed_password))
	    	
	    	# If the procedure is executed successfully, then we'll commit the changes and return the success message. 
	    	data = cursor.fetchall()

	    	if len(data) is 0:
	    		conn.commit()
	    		return json.dumps({'messgage':'User created successfully !'})
	    	else:
	    		return json.dumps({'error':str(data[0])})


	    	#return json.dumps({'html':'<span>All fields good!!</span>'})
	    else:
	    	return json.dumps({'html':'<span>Enter the required fields</span>'})

	except Exception as e: 
		return json.dumps({'error':str(e)})
	finally: 
		cursor.close()
		conn.close()

# route for the sign-in interface
@app.route('/showSignin')
def showSignin():
	if session.get('user'):
		return render_template('userHome.html')
	else:
		return render_template('signin.html')

# method to validate the user which we'll call when the user submits the form
@app.route('/validateLogin', methods=['POST'])
def validateLogin():
	try: 
		_username = request.form['inputEmail']
		_password = request.form['inputPassword']


		# connect to SQL
		con = mysql.connect()

		# create cursor
		cursor = con.cursor()

		# using cursor, call stored procedure
		cursor.callproc('sp_validateLogin', (_username,))

		# get fetched records from cursor
		data = cursor.fetchall()


		# if data has some records, match passwords against password entered by user
		if len(data) > 0:
			# check if the returned hash password matches the password entered by the user
			if check_password_hash(str(data[0][3]),_password):
				# set session variable
				session['user'] = data[0][0]
				return redirect('/userHome')
			else:
				return render_template('error.html', error = 'Wrong Email address or Password. ')
		else:
			return render_template('error.html', error = 'Wrong Email address or Password. ')

	except Exception as e:
		return render_template('error.html', error = str(e))
	finally: 
		cursor.close()
		con.close()

# create route for successful signin to user home page
@app.route('/userHome')
def userHome():
	# check the session variable before rendering home page
	if session.get('user'):
		return render_template('userHome.html')
	else:
		return render_template('error.html', error = 'Unauthorized Access')

# create a method for logout
@app.route('/logout')
def logout():
	# make the session variable user null and redirect the user to the main page
	session.pop('user', None)
	return redirect('/')

# create a method to display add wish page
@app.route('/showAddWish')
def showAddWish():
	return render_template('addWish.html')

# create method to add wish
@app.route('/addWish', methods=['POST'])
def addWish():
	try:
	# need to validate if it's an authentic call by checking if the session variable user exists
		if session.get('user'):
			# Once we have validated the session, we'll read the posted title and description
			_title = request.form['inputTitle']
			_description = request.form['inputDescription']
			_user = session.get('user')	

			# Once we have required input values, open MySQL connection and call stored procedure to add wish
			conn = mysql.connect()
			cursor = conn.cursor()
			cursor.callproc('sp_addWish', (_title, _description, _user))
			data = cursor.fetchall()

			# After executed stored procedure, commit changes to database
			if len(data) is 0:
				conn.commit()
				return redirect('/userHome')
			else: 
				return render_template('error.html', error = "An error occured!")
		else:
			return render_template('error.html', error = "Unauthorized Access")

	except Exception as e:
		return render_template('error.html', error = str(e))
	finally:
		cursor.close()
		conn.close()


# create method to call sp_GetWishByUser to get wishes created by user
@app.route('/getWish', methods=['POST'])
def getWish():
	try:
		# method can only be called with a valid user session
		if session.get('user'):
			_user = session.get('user')
			_limit = pageLimit
			_offset = request.form['offset']
			print _offset
			_total_records = 0

			# once validated, make connection to MySQL
			conn = mysql.connect()
			cursor = conn.cursor()
			cursor.callproc('sp_GetWishByUser', (_user, _limit, _offset, _total_records))
			wishes = cursor.fetchall()
 
			# close cursor and open a new one to select returned out parameter
			cursor.close()

			cursor = conn.cursor()
			cursor.execute('SELECT @_sp_GetWishByUser_3');

			outParam = cursor.fetchall()

			# once we have fetched data from MySQL, parse and convert to a dictionary so it is easy to return as JSON
			# we'll make the wish list dictionary into another list and then add the wish list and record count to the main list.
			response = []
			wishes_dict = []

			for wish in wishes:
				wish_dict = {
						'Id': wish[0],
						'Title': wish[1],
						'Description': wish[2],
						'Date': wish[4]}
				wishes_dict.append(wish_dict)

			response.append(wishes_dict)
			response.append({'total': outParam[0][0]})

			return json.dumps(response)

		else:
			return render_template('error.html', error = "Unauthorized Access")
	except Exception as e:
		return render_template('error.html', error = str(e))

# create method to get wish details from database
@app.route('/getWishById', methods=['POST'])
def getWishById():
	print 'entering getWishById'
	try:
		# if valid user session
		if session.get('user'):

			# pass in wish ID	
			_id = request.form['id']
			_user = session.get('user')

			# open connection with MySQL
			conn = mysql.connect()
			cursor = conn.cursor()
			cursor.callproc('sp_GetWishById', (_id, _user))
			result = cursor.fetchall()

			# once data is fetched, convert it to a list
			wish = []
			wish.append({'Id':result[0][0], 'Title':result[0][1], 'Description':result[0][2]})

			return json.dumps(wish)

		else:
			return render_template('error.html', error = 'Unauthorized Access')
	except Exception as e:
		return render_template('error.html', error = str(e))


# create method to update a wish
@app.route('/updateWish', methods=['POST'])
def updateWish():
	print 'entering updateWish'
	try:
		if session.get('user'):
			_user = session.get('user')
			_title = request.form['title']
			_description = request.form['description']
			_wish_id = request.form['id']

			conn = mysql.connect()
			cursor = conn.cursor()
			cursor.callproc('sp_updateWish', (_title, _description, _wish_id, _user))
			data = cursor.fetchall()

			if len(data) is 0:
				conn.commit()
				return json.dumps({'status':'OK'})
			else:
				return json.dumps({'status':'ERROR'})
	except Exception as e:
		return render_template('error.html', error = "Unauthorized Access")
	finally:
		cursor.close()
		conn.close()

# create method for wish deletion
@app.route('/deleteWish', methods=['POST'])
def deleteWish():
	print 'entering deleteWish'
	try:
		if session.get('user'):
			_user = session.get('user')
			_id = request.form['id']
			print _user, _id

			conn = mysql.connect()
			cursor = conn.cursor()
			cursor.callproc('sp_deleteWish', (_id, _user))
			result = cursor.fetchall()
			print result

			if len(result) is 0:
				conn.commit()
				return json.dumps({'status': 'OK'})
			else:
				return json.dumps({'status': 'ERROR'})
		else:
			return render_template('error.html', error = "Unauthorized Access")
	except Exception as e:
		return json.dumps({'status': str(e)})
	finally:
		cursor.close()
		conn.close()


# Next, check if the executed file is the main program and run the app:
if __name__ == "__main__":
    app.run()
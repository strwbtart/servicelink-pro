from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "servicelink_secret_key"

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS User (
        UserID INTEGER PRIMARY KEY AUTOINCREMENT,
        FirstName TEXT NOT NULL,
        LastName TEXT NOT NULL,
        Email TEXT UNIQUE NOT NULL,
        Password TEXT NOT NULL,
        UserType TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Provider (
        ProviderID INTEGER PRIMARY KEY AUTOINCREMENT,
        ProviderName TEXT NOT NULL,
        ServiceCategory TEXT NOT NULL,
        TravelRadius INTEGER,
        BackgroundCheckStatus TEXT,
        Rating REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS JobRequest (
        JobID INTEGER PRIMARY KEY AUTOINCREMENT,
        Description TEXT NOT NULL,
        Location TEXT NOT NULL,
        Category TEXT NOT NULL,
        Status TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS JobAssignment (
        AssignmentID INTEGER PRIMARY KEY AUTOINCREMENT,
        JobID INTEGER NOT NULL,
        ProviderID INTEGER NOT NULL,
        AgreedPrice REAL NOT NULL,
        FOREIGN KEY (JobID) REFERENCES JobRequest(JobID),
        FOREIGN KEY (ProviderID) REFERENCES Provider(ProviderID)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Payment (
        PaymentID INTEGER PRIMARY KEY AUTOINCREMENT,
        JobID INTEGER NOT NULL,
        Amount REAL NOT NULL,
        PaymentStatus TEXT NOT NULL,
        FOREIGN KEY (JobID) REFERENCES JobRequest(JobID)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Review (
        ReviewID INTEGER PRIMARY KEY AUTOINCREMENT,
        JobID INTEGER NOT NULL,
        Rating INTEGER NOT NULL CHECK(Rating >= 1 AND Rating <= 5),
        Comments TEXT,
        FOREIGN KEY (JobID) REFERENCES JobRequest(JobID)
    )
    """)

    cursor.execute("SELECT COUNT(*) FROM Provider")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO Provider
        (ProviderName, ServiceCategory, TravelRadius, BackgroundCheckStatus, Rating)
        VALUES
        ('Joe Martinez', 'Plumbing', 50, 'Passed', 4.8),
        ('Jane Lopez', 'Cleaning', 20, 'Passed', 4.9),
        ('Mike Garcia', 'HVAC', 60, 'Passed', 4.7)
        """)

    conn.commit()
    conn.close()

init_db()

def require_login():
    return 'user_id' in session

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        user_type = request.form['user_type']

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        try:
            cursor.execute("""
            INSERT INTO User
            (FirstName, LastName, Email, Password, UserType)
            VALUES (?, ?, ?, ?, ?)
            """, (first_name, last_name, email, password, user_type))

            conn.commit()
            conn.close()

            return redirect('/login')

        except sqlite3.IntegrityError:
            conn.close()
            return "This email already exists. Please go back and use another email."

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
        SELECT * FROM User
        WHERE Email = ? AND Password = ?
        """, (email, password))

        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['user_type'] = user[5]
            return redirect('/dashboard')
        else:
            return "Invalid email or password. Please go back and try again."

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/dashboard')
def dashboard():
    if not require_login():
        return redirect('/login')

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM JobRequest")
    jobs = cursor.fetchall()

    cursor.execute("SELECT * FROM Provider")
    providers = cursor.fetchall()

    cursor.execute("""
    SELECT JobAssignment.AssignmentID, JobRequest.Description, Provider.ProviderName, JobAssignment.AgreedPrice
    FROM JobAssignment
    JOIN JobRequest ON JobAssignment.JobID = JobRequest.JobID
    JOIN Provider ON JobAssignment.ProviderID = Provider.ProviderID
    """)
    assignments = cursor.fetchall()

    cursor.execute("SELECT * FROM Payment")
    payments = cursor.fetchall()

    cursor.execute("SELECT * FROM Review")
    reviews = cursor.fetchall()

    conn.close()

    return render_template(
        'dashboard.html',
        jobs=jobs,
        providers=providers,
        assignments=assignments,
        payments=payments,
        reviews=reviews
    )

@app.route('/create_job', methods=['GET', 'POST'])
def create_job():
    if not require_login():
        return redirect('/login')

    if request.method == 'POST':
        description = request.form['description']
        location = request.form['location']
        category = request.form['category']

        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO JobRequest
        (Description, Location, Category, Status)
        VALUES (?, ?, ?, ?)
        """, (description, location, category, "Open"))

        conn.commit()
        conn.close()

        return redirect('/dashboard')

    return render_template('create_job.html')

@app.route('/assign', methods=['GET', 'POST'])
def assign():
    if not require_login():
        return redirect('/login')

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if request.method == 'POST':
        job_id = request.form['job_id']
        provider_id = request.form['provider_id']
        agreed_price = float(request.form['agreed_price'])

        if agreed_price <= 0:
            conn.close()
            return "Price must be greater than zero. Please go back and try again."

        cursor.execute("""
        INSERT INTO JobAssignment
        (JobID, ProviderID, AgreedPrice)
        VALUES (?, ?, ?)
        """, (job_id, provider_id, agreed_price))

        cursor.execute("""
        UPDATE JobRequest
        SET Status = 'Assigned'
        WHERE JobID = ?
        """, (job_id,))

        conn.commit()
        conn.close()

        return redirect('/dashboard')

    cursor.execute("SELECT * FROM JobRequest")
    jobs = cursor.fetchall()

    cursor.execute("SELECT * FROM Provider")
    providers = cursor.fetchall()

    conn.close()

    return render_template('assign.html', jobs=jobs, providers=providers)

@app.route('/payment', methods=['GET', 'POST'])
def payment():
    if not require_login():
        return redirect('/login')

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if request.method == 'POST':
        job_id = request.form['job_id']
        amount = float(request.form['amount'])

        if amount <= 0:
            conn.close()
            return "Payment amount must be greater than zero. Please go back and try again."

        cursor.execute("""
        INSERT INTO Payment
        (JobID, Amount, PaymentStatus)
        VALUES (?, ?, ?)
        """, (job_id, amount, "Paid"))

        cursor.execute("""
        UPDATE JobRequest
        SET Status = 'Paid'
        WHERE JobID = ?
        """, (job_id,))

        conn.commit()
        conn.close()

        return redirect('/dashboard')

    cursor.execute("SELECT * FROM JobRequest")
    jobs = cursor.fetchall()

    conn.close()

    return render_template('payment.html', jobs=jobs)

@app.route('/review', methods=['GET', 'POST'])
def review():
    if not require_login():
        return redirect('/login')

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    if request.method == 'POST':
        job_id = request.form['job_id']
        rating = int(request.form['rating'])
        comments = request.form['comments']

        if rating < 1 or rating > 5:
            conn.close()
            return "Rating must be between 1 and 5. Please go back and try again."

        cursor.execute("""
        INSERT INTO Review
        (JobID, Rating, Comments)
        VALUES (?, ?, ?)
        """, (job_id, rating, comments))

        cursor.execute("""
        UPDATE JobRequest
        SET Status = 'Reviewed'
        WHERE JobID = ?
        """, (job_id,))

        conn.commit()
        conn.close()

        return redirect('/dashboard')

    cursor.execute("SELECT * FROM JobRequest")
    jobs = cursor.fetchall()

    conn.close()

    return render_template('review.html', jobs=jobs)

if __name__ == '__main__':
    app.run(debug=True)
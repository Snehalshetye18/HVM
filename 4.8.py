from decimal import Decimal
from flask import Flask, render_template, request, redirect, url_for, make_response
import pandas as pd
import boto3
from botocore.exceptions import NoCredentialsError
from boto3.dynamodb.conditions import Key, Attr
import uuid
import botocore
import io
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from pytz import timezone
from datetime import datetime
import xlsxwriter
from flask import send_file, make_response
from flask import jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, url_for, session
from functools import wraps
from flask import session, redirect, url_for
import matplotlib.pyplot as plt
import numpy as np
import os




app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a random string

# Dummy user database for demonstration
users = {'user1': generate_password_hash('password1'), 'user2': generate_password_hash('password2')}

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and check_password_hash(users[username], password):
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return 'Invalid username or password. Please try again.'
    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('index'))



@app.route('/dashboard')
def dashboard():
    if 'logged_in' in session:
        return 'Welcome, ' + session['username'] + '! <a href="/logout">Logout</a>'
    else:
        return 'You are not logged in. <a href="/login">Login</a>'

# Connect to DynamoDB
aws_access_key_id = "AKIA5FTZFJUJ6OFOAGUS"
aws_secret_access_key = "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"
aws_region = "us-east-2"
dynamodb_table_name = "envision"

dynamodb = boto3.resource('dynamodb', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key, region_name=aws_region)
table = dynamodb.Table(dynamodb_table_name)

# Connect to Amazon S3
s3_access_key_id = "AKIA5FTZFJUJ6OFOAGUS"
s3_secret_access_key = "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"
s3_region = "us-east-1"
s3_bucket_name = "envision0177"

s3 = boto3.client('s3', aws_access_key_id=s3_access_key_id, aws_secret_access_key=s3_secret_access_key, region_name=s3_region)

latest_video_id = 0

# Define Indian Standard Time (IST) timezone
local_timezone = timezone('Asia/Kolkata')

# Function to convert timestamp to IST
def convert_to_ist(timestamp_str):
    # Parse the timestamp string into a datetime object
    timestamp = datetime.strptime(timestamp_str, "%d:%m:%Y %H:%M:%S")
    # Convert the datetime object to your local timezone
    timestamp_local = timestamp.astimezone(local_timezone)
    return timestamp_local.strftime("%d:%m:%Y %H:%M:%S")

# Define a function to get the highest existing video ID from the DynamoDB table
def get_highest_video_id():
    try:
        response = table.scan()
        items = response.get('Items', [])
        if not items:  # If the table is empty, return 0
            return 0
        else:
            # Extract video IDs and find the maximum
            video_ids = [int(item['video_id']) for item in items if 'video_id' in item]
            return max(video_ids)
    except Exception as e:
        print("Error retrieving highest video ID:", e)
        return None



@app.route("/")
def default():
    return redirect(url_for('login'))

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

# Apply the login_required decorator to routes that require authentication

@app.route("/index", methods=["GET", "POST"])
@login_required
def index():
    global latest_video_id
    if request.method == "POST":
        nature_crime = request.form.get("nature_crime")
        risk_percentage = Decimal(request.form.get("risk_percentage")).quantize(Decimal('0.00001'))

        # Convert latitude and longitude to Decimal
        latitude = Decimal(request.form.get("latitude"))
        longitude = Decimal(request.form.get("longitude"))

        video_file = request.files["video_file"]
        video_data = video_file.read()

        # Get the highest existing video ID
        highest_video_id = get_highest_video_id()

        if highest_video_id is not None:
            latest_video_id = highest_video_id + 1  # Increment the highest video ID by 1
        else:
            latest_video_id = 1  # Start from 1 if there are no existing videos

        video_id = str(latest_video_id)

        video_filename = f"videos/{video_id}_{video_file.filename}"

        try:
            s3.put_object(Body=video_data, Bucket=s3_bucket_name, Key=video_filename)
        except NoCredentialsError:
            return "Amazon S3 credentials not available. Upload failed."

        # Check if the timestamp is provided by the client-side
        timestamp_str = request.form.get("timestamp")
        if timestamp_str:
            # Parse the timestamp string into a datetime object
            try:
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                # Handle invalid timestamp format
                timestamp = datetime.now()
        else:
            # If timestamp is not provided, use the current timestamp
            timestamp = datetime.now()
        timestamp_ist = convert_to_ist(timestamp.strftime("%d:%m:%Y %H:%M:%S"))

        document = {
            "video_id": video_id,
            "nature_crime": nature_crime,
            "risk_percentage": risk_percentage,
            "latitude": latitude,
            "longitude": longitude,
            "video": {
                "name": video_file.filename,
                "s3_filename": video_filename,
            },
            "timestamp": timestamp_ist # Convert datetime object to string
        }
        table.put_item(Item=document)

        return redirect(url_for("display_data", video_id=video_id))

    return render_template("index.html")

# Define the route for getting the next video ID
@app.route("/next_video_id")
def get_next_video_id():
    global latest_video_id
    latest_video_id += 1
    return str(latest_video_id)


def generate_riskometer_html(risk_percentage):
    # Logic to generate the riskometer HTML based on risk percentage
    # You can use CSS classes or JavaScript to style and animate the riskometer
    # Here's a simplified example using CSS classes:
    if risk_percentage < 30:
        return '<div class="riskometer low-risk">Low</div>'
    elif risk_percentage < 70:
        return '<div class="riskometer moderate-risk">Moderate</div>'
    else:
        return '<div class="riskometer high-risk">High</div>'



@app.route("/display_data/<video_id>")
@login_required
def display_data(video_id):
    response = table.get_item(Key={"video_id": video_id})
    item = response.get("Item")

    if item:
        latitude = float(item.get("latitude"))
        longitude = float(item.get("longitude"))

        # Generate a pre-signed URL for the video file in S3
        video_info = item.get("video", {})
        video_s3_filename = video_info.get("s3_filename", "")
        video_url = generate_presigned_url(s3_bucket_name, video_s3_filename)

        # Convert timestamp to IST
        timestamp_ist = convert_to_ist(item.get("timestamp"))

        # Generate riskometer HTML
        riskometer_html = generate_riskometer_html(item.get("risk_percentage", 0))

        return render_template("display_data.html", document=item, video_url=video_url, timestamp_ist=timestamp_ist, riskometer_html=riskometer_html)

    return "Video not found", 404



@app.route('/get-updated-data')
def get_updated_data():
    try:
        response = table.scan()
        updated_data = response.get("Items")
        return jsonify(updated_data)
    except Exception as e:
        return jsonify({"error": str(e)})





@app.route("/display_multiple_videos")
@login_required
def display_multiple_videos():
    sort_by = request.args.get("sort_by", "nature_crime")  # Default sorting by Nature of Crime
    response = table.scan()
    all_documents = response.get("Items")

    # Sort documents based on the selected criteria
    if sort_by in ["nature_crime", "risk_percentage", "video_id", "status"]:
        if sort_by == "video_id":
            all_documents.sort(key=lambda x: int(x.get(sort_by, "")))
        else:
            all_documents.sort(key=lambda x: x.get(sort_by, ""))


    return render_template("display_multiple_videos.html", videos=all_documents)



from flask import send_file

@app.route("/download_graph")
@login_required
def download_graph():
    try:
        # Retrieve data from DynamoDB
        response = table.scan()
        all_documents = response.get("Items")

        # Extract relevant data for graph (e.g., risk percentage, crime type)
        crime_data = {}  # Dictionary to store crime type as key and corresponding risk percentages as values
        for document in all_documents:
            crime_type = document.get("nature_crime", "Unknown")
            risk_percentage = float(document.get("risk_percentage", 0))
            if crime_type not in crime_data:
                crime_data[crime_type] = []
            crime_data[crime_type].append(risk_percentage)

        # Generate the graph with a specified figure size
        plt.figure(figsize=(10, 6))  # Adjust the figure size as needed

        # Plot each crime type as a separate line
        for crime_type, risk_percentages in crime_data.items():
            risk_percentages.sort()  # Sort the risk percentages for each crime type
            plt.plot(risk_percentages, marker='o', linestyle='-', label=crime_type)

        plt.title('Risk Percentage Distribution by Crime Type')
        plt.xlabel('Index')
        plt.ylabel('Risk Percentage')
        plt.grid(True)
        plt.legend()  # Show legend with crime types
        plt.tight_layout()

        # Ensure 'static' folder exists
        static_folder = os.path.join(os.getcwd(), 'static')
        if not os.path.exists(static_folder):
            os.makedirs(static_folder)

        # Save the graph to a temporary file
        graph_filename = os.path.join(static_folder, 'graph.png')
        plt.savefig(graph_filename)

        # Close the plot to free up resources
        plt.close()

        # Serve the graph image file as an attachment for download
        return send_file(graph_filename, as_attachment=True)

    except Exception as e:
        return str(e)







@app.route("/view_video/<video_id>")
def view_video(video_id):
    response = table.get_item(Key={"video_id": video_id})
    item = response.get("Item")

    if item:
        video_data = item.get("video", {}).get("data")

        if video_data:
            response = make_response(video_data)
            response.headers["Content-Type"] = "video/mp4"

            return response

    return "Video not found", 404




@app.route("/show_video_details/<video_id>")
def show_video_details(video_id):
    response = table.get_item(Key={"video_id": video_id})
    item = response.get("Item")

    if item:
        video_info = item.get("video", {})
        video_s3_filename = video_info.get("s3_filename", "")
        video_link = generate_presigned_url(s3_bucket_name, video_s3_filename)

        # Add a message based on the video's approval status
        status_message = ""
        if item.get("status") == "Approved":
            status_message = "This video has been approved."
        elif item.get("status") == "Disapproved":
            status_message = "This video has been disapproved."

        return render_template("show_video_details.html", video=item, video_link=video_link, status_message=status_message)

    return "Video not found", 404





@app.route("/approve_video/<video_id>", methods=["POST"])
def approve_video(video_id):
    # Get the Nature of Crime from DynamoDB
    response = table.get_item(Key={"video_id": video_id})
    item = response.get("Item")
    nature_of_crime = item.get("nature_crime", "Unknown")

    # Move the video to a new folder on S3 based on Nature of Crime
    old_key = f"videos/{video_id}_{item.get('video', {}).get('name', '')}"
    new_key = f"approved_videos/{nature_of_crime}/{video_id}_{item.get('video', {}).get('name', '')}"

    try:
        # Copy the object to the new key (folder-like structure)
        s3.copy_object(
            Bucket=s3_bucket_name,
            CopySource={'Bucket': s3_bucket_name, 'Key': old_key},
            Key=new_key
        )


        # Update DynamoDB item to mark video as approved
        table.update_item(
            Key={"video_id": video_id},
            UpdateExpression="SET #status_col = :status_val",
            ExpressionAttributeNames={"#status_col": "status"},
            ExpressionAttributeValues={":status_val": "Approved"}
        )

        status_message = "Video has been approved."

    except NoCredentialsError:
        return "Amazon S3 credentials not available. Move operation failed."

    return redirect(url_for('show_video_details', video_id=video_id))






@app.route("/disapprove_video/<video_id>", methods=["POST"])
def disapprove_video(video_id):
    response = table.get_item(Key={"video_id": video_id})
    item = response.get("Item")
    nature_of_crime = item.get("nature_crime", "Unknown")

    # Get the selected disapprove reason from the form
    disapprove_reason = request.form.get("disapprove_reason")

    # If disapprove_reason is "No Criminal Activity", set it to an empty string
    if disapprove_reason == "No Criminal Activity":
        disapprove_reason = "No Criminal Activity"

    # Move the video to a new folder on S3 based on the selected disapprove reason
    old_key = f"videos/{video_id}_{item.get('video', {}).get('name', '')}"
    new_key = f"disapproved_videos/{disapprove_reason}/{video_id}_{item.get('video', {}).get('name', '')}"

    try:
        # Copy the object to the new key (folder-like structure)
        s3.copy_object(
            Bucket=s3_bucket_name,
            CopySource={'Bucket': s3_bucket_name, 'Key': old_key},
            Key=new_key
        )

        table.update_item(
            Key={"video_id": video_id},
            UpdateExpression="SET #status_col = :status_val, disapprove_reason = :disapprove_reason",
            ExpressionAttributeNames={"#status_col": "status"},
            ExpressionAttributeValues={":status_val": "Disapproved", ":disapprove_reason": disapprove_reason}
        )
        status_message = "Video has been disapproved."
    except NoCredentialsError:
        return "Amazon S3 credentials not available. Move operation failed."

    return redirect(url_for('show_video_details', video_id=video_id))


@app.route("/download_data")
def download_data():
    response = table.scan()
    all_documents = response.get("Items")

    data_list = []
    approved_data_list = []
    disapproved_data_list = []

    for document in all_documents:
        video_info = document.get("video", {})
        video_id = document.get("video_id", "")
        video_name = video_info.get("name", "")
        video_s3_filename = video_info.get("s3_filename", "")

        s3_presigned_url = generate_presigned_url(s3_bucket_name, video_s3_filename)

        status = document.get("status", "Unknown")
        disapprove_reason = document.get("disapprove_reason", "")

        timestamp = document.get("timestamp", "")  # Get timestamp from DynamoDB


        data_dict = {
            "video_id": video_id,
            "nature_crime": document.get("nature_crime", ""),
            "risk_percentage": document.get("risk_percentage", ""),
            "latitude": document.get("latitude", ""),
            "longitude": document.get("longitude", ""),
            "video_name": video_name,
            "timestamp": timestamp,
            "status": status,
            "disapprove_reason": disapprove_reason,
            "video_link": s3_presigned_url,
            "timestamp": timestamp  # Include timestamp in data_dict
        }
        data_list.append(data_dict)

        if status == "Approved":
            approved_data_list.append(data_dict)
        elif status == "Disapproved":
            disapproved_data_list.append(data_dict)

    df_all = pd.DataFrame(data_list)
    df_approved = pd.DataFrame(approved_data_list)
    df_disapproved = pd.DataFrame(disapproved_data_list)


    # Create a BytesIO object to write the Excel file to memory
    excel_data = io.BytesIO()

    # Create an Excel writer object with XlsxWriter engine
    with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
        # Write DataFrame to sheet
        df_approved.to_excel(writer, sheet_name='Approved_Data', index=False)
        df_disapproved.to_excel(writer, sheet_name='Disapproved_Data', index=False)
        df_all.to_excel(writer, sheet_name='All_Data', index=False)

        # Get the workbook and the sheet
        workbook = writer.book
        worksheet = writer.sheets['All_Data']

        # Format timestamp column
        date_format = workbook.add_format({'num_format': 'dd:mm:yyyy hh:mm:ss'})
        worksheet.set_column('J:J', 20, date_format)

    # Move the BytesIO cursor to the beginning
    excel_data.seek(0)

    # Create a response with the Excel data
    response = make_response(excel_data.read())
    response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    response.headers["Content-Disposition"] = "attachment; filename=data.xlsx"

    return response





def generate_presigned_url(bucket_name, object_name, expiration= 2630000 ):
    try:
        s3_client = boto3.client('s3', aws_access_key_id=s3_access_key_id, aws_secret_access_key=s3_secret_access_key, region_name=s3_region)
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': object_name},
            ExpiresIn=expiration
        )
        print(f"Generated URL: {url}")  # Add this line for debugging
        return url
    except NoCredentialsError:
        print("S3 credentials not available. URL generation failed.")
        return None
    except Exception as e:
        print(f"An error occurred while generating the pre-signed URL: {e}")
        return None



@app.route("/download_video", methods=["POST"])
def download_video():
    if request.method == "POST":
        video_id = request.form.get("video_id")

        # Retrieve the video data from DynamoDB based on the video ID
        response = table.get_item(Key={"video_id": video_id})
        item = response.get("Item")

        if item:
            video_info = item.get("video", {})
            video_s3_filename = video_info.get("s3_filename", "")

            # Generate a presigned URL for downloading the video
            video_url = generate_presigned_url(s3_bucket_name, video_s3_filename)

            # Redirect the user to the presigned URL for downloading the video
            return redirect(video_url)

    return "Video not found", 404







@app.route('/realtime_graph')
@login_required
def realtime_graph():
    return render_template('realtime_graph.html')

# Endpoint to fetch real-time data from the backend
@app.route("/real-time-data")
@login_required
def real_time_data():
    # Redirect to the URL where your Streamlit dashboard is running
    return redirect("https://envisionai.streamlit.app/", code=302)





if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

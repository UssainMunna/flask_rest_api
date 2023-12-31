from passlib.hash import pbkdf2_sha256
from flask import Flask,request,render_template
from flask_pymongo import pymongo
from flask import jsonify 
from flask_jwt_extended import JWTManager, create_access_token,get_jwt_identity,jwt_required
from bson import ObjectId
import os


app = Flask(__name__)
jwt = JWTManager(app)

# #Database URI and JWT secret key
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY")


#connect to mongo atlas
def connect_to_mongo():
    client = pymongo.MongoClient(app.config["MONGO_URI"])
    return client['user_data']


@app.route('/')
def index():
    return render_template("index.html")

#Register a new user
@app.route("/register", methods=["POST"])
def register():
    try:user_data = request.json
    except:return jsonify({"error": f"Missing payload"}), 400
    db = connect_to_mongo()
    collection = db["users"]
    
    # Validate required fields
    required_fields = ["first_name", "last_name", "email", "password"]
    missing_fields = [field for field in required_fields if field not in user_data]
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
    # Validate unique username/email
    existing_user = collection.find_one({"email": user_data["email"]})
    if existing_user:
        return jsonify({"error": "Email already exists."}), 400
    #encrypt password 
    password = user_data['password']
    encrypted_password = pbkdf2_sha256.hash(password)
    # Insert new user
    new_user = {
        "first_name": user_data["first_name"],
        "last_name": user_data["last_name"],
        "email": user_data["email"],
        "password": encrypted_password
    }
    result = collection.insert_one(new_user)
    return jsonify({"message": "User registered successfully.", "user_id": str(result.inserted_id)})

#Login as a user
@app.route("/login", methods=["POST"])
def login():
    try:user_data = request.json
    except:return jsonify({"error": f"Missing payload"}), 400
    db = connect_to_mongo()
    collection = db["users"]
    #Validate required fields
    required_fields = ["email", "password"]
    missing_fields = [field for field in required_fields if field not in user_data]
    if missing_fields:return jsonify({"error": f"Username and Password are required: {', '.join(missing_fields)}"}), 400
    #Validate user exist
    existing_user = collection.find_one({"email": user_data["email"]})

    #verify hashed password
    if existing_user and pbkdf2_sha256.verify(user_data['password'],existing_user['password']):
        access_token = create_access_token(identity=existing_user['email'])
        return jsonify({ "message" : "User loggedin","access_token": access_token}), 200
    else:
        return jsonify({"error": "Invalid Credentials"}), 400

#create a template with jwt authorization
@app.route("/template", methods=["POST"])
@jwt_required()
def insert_template():
    try:template_data = request.json
    except:return jsonify({"error": f"Missing payload"}), 400
    db = connect_to_mongo()
    collection = db["templates"]
    # Extract User mail using jwt identity
    user_email = get_jwt_identity()
    required_fields = ["template_name", "subject", "body"]
    missing_fields = [field for field in required_fields if field not in template_data]
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
    # Add the user's email to the template data
    template_data["user_email"] = user_email  
    result = collection.insert_one(template_data)
    return jsonify({"message": "Template inserted successfully.", "template_id": str(result.inserted_id)})

#Get all template of specific user with jwt authorization
@app.route("/template", methods=["GET"])
@jwt_required()
def get_all_templates():
    db = connect_to_mongo()
    collection = db["templates"]
    # Extract User mail using jwt identity
    user_email = get_jwt_identity()
    templates = collection.find({"user_email": user_email})
    template_list = []
    for template in templates:
        # Convert ObjectId to string for JSON serialization
        template["_id"] = str(template["_id"])  
        template_list.append(template)
    return jsonify(template_list)

#Get one template of specific user with jwt authorization
@app.route("/template/<template_id>", methods=["GET"])
@jwt_required()
def get_one_templates(template_id):
    db = connect_to_mongo()
    collection = db["templates"]
    # Extract User mail using jwt identity
    user_email = get_jwt_identity()
    template = collection.find_one({"_id": ObjectId(template_id), "user_email": user_email})
    if template:
        # Convert ObjectId to string for JSON serialization
        template["_id"] = str(template["_id"])  
        return jsonify(template)
    else:return jsonify({"message": "Template not found."}), 404

#Update template of specific user with jwt authorization
@app.route("/template/<template_id>", methods=["PUT"])
@jwt_required()
def update_template(template_id):
    try:template_data = request.json
    except:return jsonify({"error": f"Missing payload"}), 400
    db = connect_to_mongo()
    collection = db["templates"]
    # Extract User mail using jwt identity
    user_email = get_jwt_identity()
    required_fields = ["template_name", "subject", "body"]
    missing_fields = [field for field in required_fields if field not in template_data]
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
    template = collection.find_one({"_id": ObjectId(template_id), "user_email": user_email})
    if template:
        #Update values using set attribute
        collection.update_one({"_id": ObjectId(template_id), "user_email": user_email},{"$set": template_data})
        return jsonify({"message": "Template updated successfully."})
    else:return jsonify({"message": "Template not found."}), 404
    
#Delete template of specific user with jwt authorization
@app.route("/template/<template_id>", methods=["DELETE"])
@jwt_required()
def delete_template(template_id):
    db = connect_to_mongo()
    collection = db["templates"]
    # Extract User mail using jwt identity
    user_email = get_jwt_identity()
    #Deleting template using ObjectId
    result = collection.delete_one({"_id": ObjectId(template_id), "user_email": user_email})
    if result.deleted_count ==1:return jsonify({"message": "Template deleted successfully."})
    else:return jsonify({"message": "Template not found."}), 404



if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0")
    
    